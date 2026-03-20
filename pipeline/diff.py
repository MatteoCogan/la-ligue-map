"""
Gestion des diffs entre versions.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime
from logger import setup_logger
from models import MapData

logger = setup_logger(__name__)


class DiffManager:
    """Gestionnaire de diff entre versions."""
    
    def __init__(self, backup_dir: Path):
        """
        Initialiser le gestionnaire de diff.
        
        Args:
            backup_dir: Répertoire de stockage des backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def compute_checksum(data: MapData) -> str:
        """
        Calculer un checksum des données.
        
        Args:
            data: Données à checksummer
            
        Returns:
            Checksum SHA256
        """
        data_str = json.dumps(
            data.dict(),
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def create_backup(self, data: MapData, prefix: str = "backup") -> Path:
        """
        Créer un backup des données.
        
        Args:
            data: Données à backuper
            prefix: Préfixe du fichier de backup
            
        Returns:
            Chemin du fichier de backup
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{prefix}_{timestamp}.json"
        backup_path = self.backup_dir / filename
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data.dict(), f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Backup créé: {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Erreur lors de la création du backup: {e}")
            raise
    
    def compare_data(
        self,
        before: MapData,
        after: MapData
    ) -> Dict[str, Any]:
        """
        Comparer deux versions de MapData.
        
        Args:
            before: Données avant
            after: Données après
            
        Returns:
            Dict avec les différences
        """
        checksum_before = self.compute_checksum(before)
        checksum_after = self.compute_checksum(after)
        
        before_coords = {(c.lat, c.lng, tuple(c.extra.tags)): c for c in before.customCoordinates}
        after_coords = {(c.lat, c.lng, tuple(c.extra.tags)): c for c in after.customCoordinates}
        
        added = []
        removed = []
        modified = []
        
        # Coordonnées ajoutées
        for key, coord in after_coords.items():
            if key not in before_coords:
                added.append(coord.dict())
        
        # Coordonnées supprimées
        for key, coord in before_coords.items():
            if key not in after_coords:
                removed.append(coord.dict())
        
        # Coordonnées modifiées
        for key, after_coord in after_coords.items():
            if key in before_coords:
                before_coord = before_coords[key]
                if before_coord.dict() != after_coord.dict():
                    modified.append({
                        "before": before_coord.dict(),
                        "after": after_coord.dict()
                    })
        
        return {
            "checksum_before": checksum_before,
            "checksum_after": checksum_after,
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified),
                "unchanged": len(set(before_coords.keys()) & set(after_coords.keys())) - len(modified)
            },
            "details": {
                "added": added[:5],  # Seulement les 5 premiers
                "removed": removed[:5],
                "modified": modified[:5]
            }
        }
    
    def save_diff_report(
        self,
        diff_data: Dict[str, Any],
        prefix: str = "diff"
    ) -> Path:
        """
        Sauvegarder un rapport de diff.
        
        Args:
            diff_data: Données de diff
            prefix: Préfixe du fichier
            
        Returns:
            Chemin du fichier de rapport
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{prefix}_{timestamp}.json"
        report_path = self.backup_dir / filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(diff_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Rapport de diff sauvegardé: {report_path}")
            return report_path
        
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du rapport: {e}")
            raise
    
    def print_diff_summary(self, diff_data: Dict[str, Any]) -> None:
        """
        Afficher un résumé des diffs.
        
        Args:
            diff_data: Données de diff
        """
        summary = diff_data.get('summary', {})
        
        logger.info("=" * 50)
        logger.info("RÉSUMÉ DES DIFFÉRENCES")
        logger.info("=" * 50)
        logger.info(f"Ajoutées:   {summary.get('added', 0):5d}")
        logger.info(f"Supprimées: {summary.get('removed', 0):5d}")
        logger.info(f"Modifiées:  {summary.get('modified', 0):5d}")
        logger.info(f"Inchangées: {summary.get('unchanged', 0):5d}")
        logger.info("=" * 50)
