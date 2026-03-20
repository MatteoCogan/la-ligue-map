"""
Chargement des données depuis local ou remote.
"""
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Tuple
from logger import setup_logger
from config import SOURCE_FILE_LOCAL, SOURCE_FILE_CACTUS, SOURCE_URL, SOURCE_URL_CACTUS, DOWNLOAD_TIMEOUT, DOWNLOAD_RETRIES
from models import SourceMapItem

logger = setup_logger(__name__)


class Loader:
    """Gestionnaire de chargement des données source."""
    
    def __init__(self, source: str = "auto"):
        """
        Initialiser le loader.
        
        Args:
            source: "local" (fichier local), "remote" (URL), ou "auto" (local si existe, sinon remote)
        """
        self.source = source
        self.data = None
    
    def load(self) -> List[Dict[str, Any]]:
        """
        Charger les données de toutes les sources.
        
        Returns:
            Liste des items source avec tags de source
            
        Raises:
            FileNotFoundError: Si fichier local absent et source="local"
            requests.RequestException: Si erreur lors du téléchargement
            json.JSONDecodeError: Si JSON invalide
        """
        all_data = []
        
        # Charger la source principale (La Ligue)
        if self.source == "local" or (self.source == "auto" and SOURCE_FILE_LOCAL.exists()):
            logger.info("Chargement depuis fichier local (La Ligue)")
            data_ligue = self._load_local(SOURCE_FILE_LOCAL)
        else:
            logger.info("Chargement depuis URL remote (La Ligue)")
            data_ligue = self._load_remote(SOURCE_URL, SOURCE_FILE_LOCAL)
        
        # Ajouter le tag "La Ligue" à chaque item
        for item in data_ligue:
            if 'tags' not in item:
                item['tags'] = []
            item['tags'].append("La Ligue")
        
        all_data.extend(data_ligue)
        
        # Charger la source Cactus
        try:
            if self.source == "local" or (self.source == "auto" and SOURCE_FILE_CACTUS.exists()):
                logger.info("Chargement depuis fichier local (Cactus)")
                data_cactus = self._load_local(SOURCE_FILE_CACTUS)
            else:
                logger.info("Chargement depuis URL remote (Cactus)")
                data_cactus = self._load_remote(SOURCE_URL_CACTUS, SOURCE_FILE_CACTUS)
            
            # Ajouter le tag "Cactus" à chaque item
            for item in data_cactus:
                if 'tags' not in item:
                    item['tags'] = []
                item['tags'].append("Cactus")
            
            all_data.extend(data_cactus)
            logger.info(f"Chargé {len(data_cactus)} items depuis source Cactus")
        
        except Exception as e:
            logger.warning(f"Impossible de charger la source Cactus: {e}")
        
        logger.info(f"Total: {len(all_data)} items chargés (La Ligue: {len(data_ligue)}, Cactus: {len(data_cactus) if 'data_cactus' in locals() else 0})")
        self.data = all_data
        return all_data
    
    def _load_local(self, filepath: Path) -> List[Dict[str, Any]]:
        """Charger depuis fichier local."""
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier source local absent: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Chargé {len(data)} items depuis {filepath}")
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans le fichier local: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors du chargement local: {e}")
            raise
    
    def _load_remote(self, url: str, cache_path: Path) -> List[Dict[str, Any]]:
        """Charger depuis URL remote avec retry."""
        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            try:
                logger.info(f"Tentative {attempt}/{DOWNLOAD_RETRIES} de téléchargement depuis {url}")
                
                response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Chargé {len(data)} items depuis URL remote")
                
                # Sauvegarder en local pour cache
                self._save_local_cache(data, cache_path)
                return data
            
            except requests.RequestException as e:
                if attempt < DOWNLOAD_RETRIES:
                    logger.warning(f"Erreur téléchargement (tentative {attempt}): {e}, retry...")
                    continue
                else:
                    logger.error(f"Impossible de télécharger après {DOWNLOAD_RETRIES} tentatives: {e}")
                    raise
            
            except json.JSONDecodeError as e:
                logger.error(f"Erreur JSON depuis URL remote: {e}")
                raise
    
    def _save_local_cache(self, data: List[Dict[str, Any]], cache_path: Path) -> None:
        """Sauvegarder les données téléchargées en cache local."""
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cache local sauvegardé dans {cache_path}")
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder le cache local: {e}")
    
    def validate_structure(self) -> bool:
        """
        Valider la structure basique des données.
        
        Returns:
            True si structure valide
        """
        if not self.data or not isinstance(self.data, list):
            logger.error("Les données doivent être une liste")
            return False
        
        if len(self.data) == 0:
            logger.warning("Les données sont vides")
            return False
        
        # Vérifier le premier item
        first_item = self.data[0]
        required_keys = {'link', 'name', 'tags', 'coordinates'}
        
        if not required_keys.issubset(first_item.keys()):
            logger.error(f"Clés manquantes. Requis: {required_keys}, obtenu: {set(first_item.keys())}")
            return False
        
        logger.info(f"Structure validée: {len(self.data)} items avec les bonnes clés")
        return True
