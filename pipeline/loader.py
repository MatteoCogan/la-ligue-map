"""
Chargement des donnees depuis local ou remote.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from config import (
    DOWNLOAD_RETRIES,
    DOWNLOAD_TIMEOUT,
    SOURCE_FILE_CACTUS,
    SOURCE_FILE_LOCAL,
    SOURCE_URL,
    SOURCE_URL_CACTUS,
)
from logger import setup_logger

logger = setup_logger(__name__)


class Loader:
    """Gestionnaire de chargement des donnees source."""

    def __init__(self, source: str = "auto", datasets: str = "both"):
        """
        Initialiser le loader.

        Args:
            source: "local" (fichier local), "remote" (URL), ou "auto"
            datasets: "la-ligue", "cactus" ou "both"
        """
        self.source = source
        self.datasets = datasets
        self.data = None

    def load(self) -> List[Dict[str, Any]]:
        """
        Charger les donnees des sources selectionnees.

        Returns:
            Liste des items source avec tags de source
        """
        all_data: List[Dict[str, Any]] = []
        data_ligue: List[Dict[str, Any]] = []
        data_cactus: List[Dict[str, Any]] = []

        if self.datasets in {"la-ligue", "both"}:
            data_ligue = self._load_dataset(
                dataset_name="La Ligue",
                local_path=SOURCE_FILE_LOCAL,
                remote_url=SOURCE_URL,
                source_tag="La Ligue",
            )
            all_data.extend(data_ligue)

        if self.datasets in {"cactus", "both"}:
            try:
                data_cactus = self._load_dataset(
                    dataset_name="Cactus",
                    local_path=SOURCE_FILE_CACTUS,
                    remote_url=SOURCE_URL_CACTUS,
                    source_tag="Cactus",
                )
                all_data.extend(data_cactus)
                logger.info(f"Charge {len(data_cactus)} items depuis source Cactus")
            except Exception as exc:
                logger.warning(f"Impossible de charger la source Cactus: {exc}")

        logger.info(
            f"Total: {len(all_data)} items charges "
            f"(La Ligue: {len(data_ligue)}, Cactus: {len(data_cactus)})"
        )
        self.data = all_data
        return all_data

    def _load_dataset(
        self,
        dataset_name: str,
        local_path: Path,
        remote_url: str,
        source_tag: str,
    ) -> List[Dict[str, Any]]:
        """Charger une source individuelle et y injecter son tag d'origine."""
        if self.source == "local" or (self.source == "auto" and local_path.exists()):
            logger.info(f"Chargement depuis fichier local ({dataset_name})")
            data = self._load_local(local_path)
        else:
            logger.info(f"Chargement depuis URL remote ({dataset_name})")
            data = self._load_remote(remote_url, local_path)

        for item in data:
            if "tags" not in item:
                item["tags"] = []
            item["tags"].append(source_tag)

        return data

    def _load_local(self, filepath: Path) -> List[Dict[str, Any]]:
        """Charger depuis fichier local."""
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier source local absent: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)

            logger.info(f"Charge {len(data)} items depuis {filepath}")
            return data

        except json.JSONDecodeError as exc:
            logger.error(f"Erreur JSON dans le fichier local: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Erreur lors du chargement local: {exc}")
            raise

    def _load_remote(self, url: str, cache_path: Path) -> List[Dict[str, Any]]:
        """Charger depuis URL remote avec retry."""
        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            try:
                logger.info(
                    f"Tentative {attempt}/{DOWNLOAD_RETRIES} de telechargement depuis {url}"
                )

                response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Charge {len(data)} items depuis URL remote")

                self._save_local_cache(data, cache_path)
                return data

            except requests.RequestException as exc:
                if attempt < DOWNLOAD_RETRIES:
                    logger.warning(
                        f"Erreur telechargement (tentative {attempt}): {exc}, retry..."
                    )
                    continue

                logger.error(
                    f"Impossible de telecharger apres {DOWNLOAD_RETRIES} tentatives: {exc}"
                )
                raise

            except json.JSONDecodeError as exc:
                logger.error(f"Erreur JSON depuis URL remote: {exc}")
                raise

        raise RuntimeError("Chargement distant impossible")

    def _save_local_cache(self, data: List[Dict[str, Any]], cache_path: Path) -> None:
        """Sauvegarder les donnees telechargees en cache local."""
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as file_handle:
                json.dump(data, file_handle, indent=2, ensure_ascii=False)
            logger.info(f"Cache local sauvegarde dans {cache_path}")
        except Exception as exc:
            logger.warning(f"Impossible de sauvegarder le cache local: {exc}")

    def validate_structure(self) -> bool:
        """Valider la structure basique des donnees."""
        if not self.data or not isinstance(self.data, list):
            logger.error("Les donnees doivent etre une liste")
            return False

        if len(self.data) == 0:
            logger.warning("Les donnees sont vides")
            return False

        first_item = self.data[0]
        required_keys = {"link", "name", "tags", "coordinates"}

        if not required_keys.issubset(first_item.keys()):
            logger.error(
                f"Cles manquantes. Requis: {required_keys}, obtenu: {set(first_item.keys())}"
            )
            return False

        logger.info(f"Structure validee: {len(self.data)} items avec les bonnes cles")
        return True
