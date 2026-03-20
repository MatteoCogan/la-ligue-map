"""
Transformation des données depuis le format source vers le format map-making.app.
"""
import json
import re
from typing import List, Dict, Any, Set
from datetime import datetime
from logger import setup_logger
from models import MapData, Coordinate, Extra, SourceMapItem

try:
    import reverse_geocoder as rg
    HAS_REVERSE_GEOCODER = True
except ImportError:
    HAS_REVERSE_GEOCODER = False

logger = setup_logger(__name__)


class Transformer:
    """Transforme les données du format source vers le format map-making.app."""
    
    def __init__(self, skip_duplicates: bool = True):
        """
        Initialiser le transformer.
        
        Args:
            skip_duplicates: Si True, ignore les coordonnées dupliquées (même lat/lng)
        """
        self.skip_duplicates = skip_duplicates
        self.country_cache = {}  # Cache pour les pays (lat, lng) -> pays
        
        # Initialiser reverse_geocoder si disponible
        if HAS_REVERSE_GEOCODER:
            try:
                # Charger les données de reverse_geocoder (télécharge automatiquement si nécessaire)
                logger.info("Initialisation de reverse_geocoder...")
            except Exception as e:
                logger.warning(f"Impossible d'initialiser reverse_geocoder: {e}")
    
    def transform(self, source_data: List[Dict[str, Any]]) -> MapData:
        """
        Transformer les données source.
        
        Args:
            source_data: Liste des items source du fichier coordinatesAllTags.json
            
        Returns:
            MapData compatible map-making.app
        """
        logger.info(f"Début de la transformation de {len(source_data)} items")
        
        coordinates: List[Coordinate] = []
        stats = {
            'total_coords': 0,
            'transformed_coords': 0,
            'duplicates_skipped': 0,
            'errors': 0,
        }
        
        for item_idx, item in enumerate(source_data):
            try:
                # Valider la structure de base
                if not self._validate_source_item(item):
                    stats['errors'] += 1
                    continue
                
                map_link = item['link']
                map_name = item['name']
                map_tags = item.get('tags', [])
                
                # Boucler sur chaque coordonnée
                for coord in item.get('coordinates', []):
                    stats['total_coords'] += 1
                    
                    try:
                        # Créer l'objet Coordinate
                        new_coord = self._create_coordinate(
                            coord,
                            map_tags,
                            map_link,
                            map_name
                        )
                        
                        # Ajouter la coordonnée (pas de déduplication)
                        coordinates.append(new_coord)
                        stats['transformed_coords'] += 1
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la transformation d'une coordonnée: {e}")
                        stats['errors'] += 1
                        continue
            
            except Exception as e:
                logger.error(f"Erreur lors de la transformation de l'item {item_idx}: {e}")
                stats['errors'] += 1
                continue
        
        # Créer l'objet MapData final
        map_data = MapData(
            name="La ligue",
            customCoordinates=coordinates
        )
        
        logger.info(
            f"Transformation complétée: "
            f"{stats['transformed_coords']} coordonnées transformées, "
            f"{stats['errors']} erreurs"
        )
        
        return map_data
    
    def _validate_source_item(self, item: Dict[str, Any]) -> bool:
        """Valider la structure d'un item source."""
        required_keys = {'link', 'name', 'tags', 'coordinates'}
        
        if not required_keys.issubset(item.keys()):
            logger.warning(f"Item invalide, clés manquantes: {required_keys - set(item.keys())}")
            return False
        
        if not isinstance(item.get('coordinates'), list):
            logger.warning("Field 'coordinates' doit être une liste")
            return False
        
        return True
    
    def _create_coordinate(
        self,
        coord: Dict[str, Any],
        map_tags: List[str],
        map_link: str,
        map_name: str
    ) -> Coordinate:
        """
        Créer un objet Coordinate à partir des données source.
        
        Args:
            coord: Coordonnée source
            map_tags: Tags de la map
            map_link: Link de la map
            map_name: Nom de la map
            
        Returns:
            Coordinate transformée
        """
        # Construire les tags enrichis
        tags = set()
        
        # Ajouter les tags originaux
        for tag in (map_tags or []):
            tags.add(tag)
            # Extraire et ajouter les sous-tags
            subtags = self._extract_subtags(tag)
            tags.update(subtags)
        
        # tags.append("Move")
        tags.add(f"link={map_link}")
        tags.add(map_name)
        
        # Ajouter des tags du nom de la map si des modes GeoGuessr y sont trouvés
        map_modes = self._extract_geoguessr_modes(map_name)
        tags.update(map_modes)
        
        # Ajouter le tag du pays basé sur les coordonnées
        country = self._get_country_tag(float(coord['lat']), float(coord['lng']))
        if country:
            tags.add(country)
        
        # Créer l'objet Coordinate
        return Coordinate(
            lat=float(coord['lat']),
            lng=float(coord['lng']),
            heading=self._normalize_heading(float(coord.get('heading', 0))),
            pitch=float(coord.get('pitch', 0)),
            zoom=float(coord.get('zoom', 0)),
            panoId=coord.get('panoId'),
            countryCode=coord.get('countryCode'),
            stateCode=coord.get('stateCode'),
            extra=Extra(tags=list(tags)),
            createdAt=datetime.utcnow().isoformat() + 'Z'
        )
    
    def _normalize_heading(self, heading: float) -> float:
        """
        Normaliser le heading pour qu'il soit dans la plage [0, 360).
        
        Les valeurs en dehors de cette plage sont ramenées à l'équivalent dans [0, 360).
        
        Args:
            heading: Valeur de heading brute
            
        Returns:
            Valeur de heading normalisée dans [0, 360)
        """
        # Utiliser modulo pour ramener à [0, 360)
        normalized = heading % 360
        return normalized
    
    def _extract_subtags(self, tag: str) -> Set[str]:
        """
        Extraire les sous-tags intelligemment à partir d'un tag.
        
        Exemples:
        - 'S4 L3 J2 - Map 4.5 - Chasse aux points - No Move Coop'
          -> ['S4 L3', 'S4', 'L3', 'J2', 'Map 4', 'Chasse aux points', 'NM', 'Coop']
        - 'S3 (J5 - L1) Map 4.1 - Chasse aux points (NMPZ)'
          -> ['S3', 'L1', 'J5', 'Map 4', 'Chasse aux points', 'NMPZ']
        - 'S1 J4 - Royaume-Uni Speedrun'
          -> ['S1', 'J4', 'Royaume-Uni Speedrun']
        """
        subtags: Set[str] = set()
        
        # Pattern 1: Extraire S<num> L<num> J<num>
        season_pattern = r'S(\d+)\s+L(\d+)\s+J(\d+)'
        season_match = re.search(season_pattern, tag)
        if season_match:
            season = f"S{season_match.group(1)}"
            ligue = f"L{season_match.group(2)}"
            jornada = f"J{season_match.group(3)}"
            subtags.add(season)
            subtags.add(ligue)
            subtags.add(jornada)
            subtags.add(f"{season} {ligue}")  # S4 L3
        else:
            # Pattern 2: Format ancien S3 (J5 - L1)
            season_pattern_old = r'S(\d+)\s*\(\s*([^)]+)\s*\)'
            season_match_old = re.search(season_pattern_old, tag)
            if season_match_old:
                season = f"S{season_match_old.group(1)}"
                inside_parens = season_match_old.group(2)
                subtags.add(season)
                
                # Extraire J et L de l'intérieur des parenthèses
                jornada_match = re.search(r'J(\d+)', inside_parens)
                if jornada_match:
                    subtags.add(f"J{jornada_match.group(1)}")
                
                ligue_match = re.search(r'L(\d+)', inside_parens)
                if ligue_match:
                    subtags.add(f"L{ligue_match.group(1)}")
            else:
                # Pattern 3: Format S1/S2 simple (juste S<num> J<num>)
                simple_pattern = r'S(\d+)\s+J(\d+)'
                simple_match = re.search(simple_pattern, tag)
                if simple_match:
                    season = f"S{simple_match.group(1)}"
                    jornada = f"J{simple_match.group(2)}"
                    subtags.add(season)
                    subtags.add(jornada)
        
        # Pattern 4: Extraire version de la map (Map 4.5 -> Map 4)
        map_pattern = r'Map\s+(\d+)'
        map_match = re.search(map_pattern, tag)
        if map_match:
            subtags.add(f"Map {map_match.group(1)}")
        
        # Pattern 5: Modes GeoGuessr avec parenthèses (NMPZ), (NM), etc.
        geoguessr_modes_parens = re.findall(r'\(([A-Z]+)\)', tag)
        for mode in geoguessr_modes_parens:
            normalized = self._normalize_geoguessr_mode(mode)
            if normalized:
                subtags.add(normalized)
        
        # Pattern 6: Modes GeoGuessr simples (détection et normalisation)
        geoguessr_patterns = [
            (r'\bno\s*move\b|\bnm\b', 'NM', True),  # No Move, NM, no move (case-insensitive)
            (r'\bmove\b', 'Move', True),  # Move (case-insensitive)
            (r'\bnmpz\b', 'NMPZ', True),  # NMPZ (case-insensitive)
        ]
        for pattern, normalized_mode, case_insensitive in geoguessr_patterns:
            flags = re.IGNORECASE if case_insensitive else 0
            if re.search(pattern, tag, flags):
                subtags.add(normalized_mode)
        
        # Pattern 7: Thèmes/Modes spéciaux (Chasse aux points, Speedrun, Coop, etc.)
        themes = [
            'Chasse aux points', 'Speedrun', 'Coop', 'Solo', 
            'Duels', 'Sprint', 'Classique', 'Challenge'
        ]
        for theme in themes:
            if theme in tag:
                subtags.add(theme)
        
        # Pattern 8: Lieux spécifiques (Pays, villes)
        # Chercher des noms de pays/régions connus
        locations = [
            'Royaume-Uni', 'France', 'Allemagne', 'Italie', 'Espagne',
            'Portugal', 'Belgique', 'Pays-Bas', 'Suisse', 'Autriche',
            'Grèce', 'Pologne', 'Tchéquie', 'Slovaquie', 'Hongrie'
        ]
        for location in locations:
            if location in tag:
                subtags.add(location)
        
        return subtags
    
    def _normalize_geoguessr_mode(self, mode: str) -> str:
        """
        Normaliser les modes GeoGuessr pour avoir une version unique par mode.
        
        Exemples:
        - 'NM' -> 'NM'
        - 'Move' -> 'Move'
        - 'NMPZ' -> 'NMPZ'
        - Autres -> retourne le mode tel quel
        """
        mode_lower = mode.lower()
        
        # Variantes de No Move -> NM
        if mode_lower in ['nm', 'no move', 'nomove']:
            return 'NM'
        
        # Move reste Move
        if mode_lower == 'move':
            return 'Move'
        
        # Autres modes spécialisés
        if mode_lower == 'nmpz':
            return 'NMPZ'
        
        # Si on reconnaît pas, retourner tel quel
        return mode
    
    def _extract_geoguessr_modes(self, text: str) -> Set[str]:
        """Extraire et normaliser les modes GeoGuessr du texte (nom de map par exemple)."""
        modes = set()
        
        geoguessr_patterns = [
            (r'\bno\s*move\b|\bnm\b', 'NM', True),  # No Move, NM, no move (case-insensitive)
            (r'\bmove\b', 'Move', True),  # Move (case-insensitive)
            (r'\bnmpz\b', 'NMPZ', True),  # NMPZ (case-insensitive)
        ]
        
        for pattern, normalized_mode, case_insensitive in geoguessr_patterns:
            flags = re.IGNORECASE if case_insensitive else 0
            if re.search(pattern, text, flags):
                modes.add(normalized_mode)
        
        return modes
    
    def _get_country_tag(self, lat: float, lng: float) -> str:
        """
        Obtenir le nom du pays à partir des coordonnées.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Nom du pays (ou vide si impossible)
        """
        if not HAS_REVERSE_GEOCODER:
            return ""
        
        # Vérifier si déjà en cache
        coord_key = (round(lat, 4), round(lng, 4))  # Arrondir pour cache plus efficace
        if coord_key in self.country_cache:
            return self.country_cache[coord_key]
        
        try:
            # reverse_geocoder retourne (lat, lng, nom_pays)
            results = rg.search([(lat, lng)])
            if results and len(results) > 0:
                country = results[0][2]  # Index 2 = nom du pays
                self.country_cache[coord_key] = country
                return country
        except Exception as e:
            logger.debug(f"Erreur reverse_geocoding pour ({lat}, {lng}): {e}")
        
        self.country_cache[coord_key] = ""
        return ""
    
    def get_stats(self, map_data: MapData) -> Dict[str, Any]:
        """Obtenir les statistiques de la transformation."""
        return {
            'total_coordinates': len(map_data.customCoordinates),
            'coordinates_with_pano': sum(1 for c in map_data.customCoordinates if c.panoId),
            'coordinates_with_tags': sum(1 for c in map_data.customCoordinates if c.extra.tags),
            'unique_countries': len(set(c.countryCode for c in map_data.customCoordinates if c.countryCode)),
        }
