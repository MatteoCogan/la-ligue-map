"""
Upload des données vers l'API map-making.app.
"""
import requests
from typing import Dict, Any, List
from logger import setup_logger
from config import MAP_MAKING_APP_BASE_URL, API_KEY, MMA_ENDPOINTS
from models import MapData, Coordinate

logger = setup_logger(__name__)


class Uploader:
    """Gestionnaire d'upload vers map-making.app."""
    
    def __init__(self, api_key: str = None):
        """
        Initialiser l'uploader.
        
        Args:
            api_key: Clé API map-making.app (utilise celle de config si non fourni)
        """
        self.api_key = api_key or API_KEY
        if not self.api_key:
            logger.warning("Pas de clé API configurée (MMA_API_KEY)")
        
        self.base_url = MAP_MAKING_APP_BASE_URL
        self.session = requests.Session()
        self._setup_headers()
    
    def _setup_headers(self) -> None:
        """Configurer les headers par défaut."""
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"API {self.api_key}" if self.api_key else "",
        })
    
    def test_connection(self) -> bool:
        """
        Tester la connexion à l'API map-making.app.
        
        Returns:
            True si connexion OK et authentification valide
        """
        if not self.api_key:
            logger.error("Pas de clé API configurée")
            return False
        
        try:
            logger.info("Test de connexion à l'API map-making.app...")
            
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['user']}"
            response = self.session.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                user = response.json()
                logger.info(f"✓ Connexion réussie! Utilisateur: {user.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"✗ Erreur d'authentification (code {response.status_code})")
                return False
        
        except requests.RequestException as e:
            logger.error(f"✗ Impossible de se connecter: {e}")
            return False
    
    def create_map(self, name: str, public_url: str = None) -> str:
        """
        Créer une nouvelle map sur map-making.app.
        
        Args:
            name: Nom de la map
            public_url: URL publique optionnelle
            
        Returns:
            ID de la map créée
            
        Raises:
            Exception: Si erreur lors de la création
        """
        try:
            logger.info(f"Création de la map '{name}'...")
            
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['maps']}"
            payload = {
                "name": name,
                "description": ""
            }
            
            response = self.session.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            
            map_data = response.json()
            map_id = map_data.get('id')
            
            if map_id:
                logger.info(f"✓ Map créée avec ID: {map_id}")
                
                # Mettre à jour l'URL publique si fournie
                if public_url:
                    self._update_map_url(map_id, name, public_url)
                
                return map_id
            else:
                raise Exception("Pas d'ID dans la réponse")
        
        except Exception as e:
            logger.error(f"✗ Erreur lors de la création de la map: {e}")
            raise
    
    def _update_map_url(self, map_id: str, name: str, public_url: str) -> None:
        """Mettre à jour l'URL publique d'une map."""
        try:
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['map_detail'].format(mapId=map_id)}"
            payload = {
                "name": name,
                "publicUrl": public_url
            }
            
            response = self.session.put(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"URL publique mise à jour: {public_url}")
        
        except Exception as e:
            logger.warning(f"Impossible de mettre à jour l'URL publique: {e}")
    
    def import_locations(self, map_id: str, coordinates: List[Coordinate]) -> bool:
        """
        Importer des coordonnées dans une map.
        
        Args:
            map_id: ID de la map
            coordinates: Liste des coordonnées
            
        Returns:
            True si succès
            
        Raises:
            Exception: Si erreur lors de l'import
        """
        if not coordinates:
            logger.warning("Aucune coordonnée à importer")
            return True
        
        try:
            logger.info(f"Import de {len(coordinates)} coordonnées vers la map {map_id}...")
            
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['locations_import'].format(mapId=map_id)}"
            
            # Convertir les coordonnées au format map-making.app
            locations_mma = [coord.to_mma_format() for coord in coordinates]
            
            payload = {
                "edits": [{
                    "action": {"type": 4},
                    "create": locations_mma,
                    "remove": []
                }]
            }
            
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            
            logger.info(f"✓ {len(coordinates)} coordonnées importées avec succès")
            return True
        
        except requests.exceptions.Timeout:
            logger.error("✗ Timeout lors de l'import (peut-être trop de coordonnées)")
            raise
        except Exception as e:
            logger.error(f"✗ Erreur lors de l'import: {e}")
            raise
    
    def get_existing_locations(self, map_id: str) -> List[Dict[str, Any]]:
        """
        Récupérer les locations existantes d'une map.
        
        Args:
            map_id: ID de la map
            
        Returns:
            Liste des locations existantes
        """
        try:
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['locations_get'].format(mapId=map_id)}"
            response = self.session.get(endpoint, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # La réponse peut être directement une liste ou un dictionnaire
            if isinstance(data, list):
                locations = data
            elif isinstance(data, dict):
                locations = data.get('customCoordinates', [])
            else:
                locations = []
            
            logger.debug(f"Récupéré {len(locations)} locations existantes")
            return locations
        
        except Exception as e:
            logger.warning(f"Impossible de récupérer les locations existantes: {e}")
            return []
    
    def clear_map_locations(self, map_id: str) -> bool:
        """
        Supprimer toutes les locations d'une map.
        
        Args:
            map_id: ID de la map
            
        Returns:
            True si succès
        """
        try:
            # Récupérer les locations existantes
            locations = self.get_existing_locations(map_id)
            
            if not locations:
                logger.info("Aucune location à supprimer")
                return True
            
            logger.info(f"Suppression de {len(locations)} locations existantes...")
            
            endpoint = f"{self.base_url}{MMA_ENDPOINTS['locations_import'].format(mapId=map_id)}"
            
            # Extraire les IDs des locations
            # Les locations peuvent être des dicts avec 'id' ou d'autres formats
            location_ids = []
            for loc in locations:
                if isinstance(loc, dict) and loc.get('id'):
                    location_ids.append(loc.get('id'))
                elif isinstance(loc, str):
                    location_ids.append(loc)
            
            logger.debug(f"IDs à supprimer: {location_ids}")
            
            if not location_ids:
                logger.warning(f"Impossible d'extraire les IDs des {len(locations)} locations")
                return False
            
            payload = {
                "edits": [{
                    "action": {"type": 4},
                    "create": [],
                    "remove": location_ids
                }]
            }
            
            response = self.session.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
            
            logger.info(f"✓ {len(location_ids)} locations supprimées")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erreur lors de la suppression des locations: {e}")
            return False
    
    def upload_map_data(self, map_data: MapData, map_id: str = None) -> bool:
        """
        Uploader les données complètes d'une map.
        
        Args:
            map_data: Objet MapData à uploader
            map_id: ID de la map (crée une nouvelle si non fourni)
            
        Returns:
            True si succès
        """
        if not self.test_connection():
            logger.error("Impossible de se connecter à l'API")
            return False
        
        try:
            # Créer la map si nécessaire
            if not map_id:
                map_id = self.create_map(map_data.name)
            
            # Vider les locations existantes
            if map_data.customCoordinates:
                self.clear_map_locations(map_id)
            
            # Importer les nouvelles coordonnées
            if map_data.customCoordinates:
                self.import_locations(map_id, map_data.customCoordinates)
            
            logger.info(f"✓ Map complètement uploadée: {map_id}")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erreur lors de l'upload: {e}")
            return False
    
    def batch_import_by_chunks(
        self,
        map_id: str,
        coordinates: List[Coordinate],
        chunk_size: int = 500
    ) -> bool:
        """
        Importer des coordonnées par lots si la liste est trop grande.
        
        Args:
            map_id: ID de la map
            coordinates: Liste complète des coordonnées
            chunk_size: Taille des chunks (défaut 500)
            
        Returns:
            True si tous les chunks sont importés
        """
        logger.info(f"Import par chunks ({chunk_size} coords/chunk)...")
        
        total = len(coordinates)
        for i in range(0, total, chunk_size):
            chunk = coordinates[i:i+chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (total + chunk_size - 1) // chunk_size
            
            try:
                logger.info(f"Import chunk {chunk_num}/{total_chunks} ({len(chunk)} coords)...")
                self.import_locations(map_id, chunk)
            except Exception as e:
                logger.error(f"✗ Erreur lors du chunk {chunk_num}: {e}")
                return False
        
        logger.info("✓ Tous les chunks importés avec succès")
        return True
