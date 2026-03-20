"""
Validation des données transformées.
"""
import json
from typing import List, Tuple
from pydantic import ValidationError
from logger import setup_logger
from models import MapData, Coordinate

logger = setup_logger(__name__)


class Validator:
    """Validateur pour les données transformées."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_map_data(self, map_data: MapData) -> Tuple[bool, List[str]]:
        """
        Valider une MapData complète.
        
        Args:
            map_data: Données à valider
            
        Returns:
            Tuple (est_valide, liste_des_erreurs)
        """
        self.errors = []
        self.warnings = []
        
        logger.info("Début de la validation")
        
        # Validation générale
        if not map_data.name:
            self.errors.append("Le nom de la map est requis")
        
        if len(map_data.customCoordinates) == 0:
            self.errors.append("Au moins une coordonnée est requise")
        
        # Valider chaque coordonnée
        for idx, coord in enumerate(map_data.customCoordinates):
            coord_errors = self._validate_coordinate(coord, idx)
            self.errors.extend(coord_errors)
        
        # Loguer les résultats
        if self.errors:
            logger.error(f"Validation échouée avec {len(self.errors)} erreurs")
            for error in self.errors[:5]:  # Afficher les 5 premières
                logger.error(f"  - {error}")
            if len(self.errors) > 5:
                logger.error(f"  ... et {len(self.errors) - 5} autres erreurs")
            return False, self.errors
        
        if self.warnings:
            logger.warning(f"Validation réussie avec {len(self.warnings)} avertissements")
            for warning in self.warnings[:5]:
                logger.warning(f"  - {warning}")
        else:
            logger.info(f"Validation réussie: {len(map_data.customCoordinates)} coordonnées valides")
        
        return True, self.warnings
    
    def _validate_coordinate(self, coord: Coordinate, idx: int) -> List[str]:
        """Valider une coordonnée individuelle."""
        errors = []
        
        # Vérifier les ranges
        if coord.lat < -90 or coord.lat > 90:
            errors.append(f"Coord {idx}: Latitude invalide {coord.lat} (doit être entre -90 et 90)")
        
        if coord.lng < -180 or coord.lng > 180:
            errors.append(f"Coord {idx}: Longitude invalide {coord.lng} (doit être entre -180 et 180)")
        
        if coord.heading < 0 or coord.heading > 360:
            self.warnings.append(f"Coord {idx}: Heading {coord.heading} est hors range (0-360)")
        
        if coord.pitch < -90 or coord.pitch > 90:
            self.warnings.append(f"Coord {idx}: Pitch {coord.pitch} est hors range typique (-90 à 90)")
        
        # Vérifier que les tags existent
        if not coord.extra or not coord.extra.tags:
            self.warnings.append(f"Coord {idx}: Pas de tags")
        
        return errors
    
    def validate_json_schema(self, json_path: str) -> bool:
        """
        Valider un fichier JSON contre le schéma.
        
        Args:
            json_path: Chemin du fichier JSON
            
        Returns:
            True si valide
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            map_data = MapData(**data)
            return self.validate_map_data(map_data)[0]
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON invalide: {e}")
            return False
        except ValidationError as e:
            logger.error(f"Validation Pydantic échouée: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return False
    
    def get_errors(self) -> List[str]:
        """Obtenir la liste des erreurs."""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Obtenir la liste des avertissements."""
        return self.warnings
