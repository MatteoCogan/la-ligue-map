"""
Pipeline main entrypoint and orchestration.
"""

import argparse
import json
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Tuple

from config import (
    API_KEY,
    AUTO_UPLOAD,
    BACKUP_DIR,
    DRY_RUN,
    LOG_DIR,
    MAP_ID,
    OUTPUT_FILE,
    SOURCE_FILE_LOCAL,
    WATCH_DEBOUNCE_SECONDS,
)
from diff import DiffManager
from loader import Loader
from logger import setup_logger
from transformer import Transformer
from uploader import Uploader
from validator import Validator
from watcher import Watcher

logger = setup_logger(__name__)


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(
        self,
        source: str = "auto",
        output: Optional[Path] = None,
        api_key: Optional[str] = None,
        map_id: Optional[str] = None,
        auto_upload: bool = False,
        dry_run: bool = False,
    ):
        self.source = source
        self.output = Path(output) if output else OUTPUT_FILE
        self.api_key = api_key or API_KEY
        self.map_id = map_id or MAP_ID
        self.auto_upload = auto_upload or AUTO_UPLOAD
        self.dry_run = dry_run or DRY_RUN

        self.loader = Loader(source)
        self.transformer = Transformer()
        self.validator = Validator()
        self.uploader = Uploader(self.api_key) if self.api_key else None
        self.diff_manager = DiffManager(BACKUP_DIR)

    def run(self) -> bool:
        """Run the full pipeline."""
        try:
            logger.info("=" * 60)
            logger.info("DEBUT DE LA PIPELINE")
            logger.info("=" * 60)
            start_time = datetime.now()

            logger.info("\n[1/5] Chargement des donnees...")
            source_data = self.loader.load()

            if not self.loader.validate_structure():
                logger.error("Structure source invalide")
                return False

            logger.info("\n[2/5] Transformation...")
            map_data = self.transformer.transform(source_data)
            previous_map_data = self._load_previous_output()
            self._preserve_existing_created_at(previous_map_data, map_data)
            transform_stats = self.transformer.get_stats(map_data)

            logger.info(f"  - {transform_stats['total_coordinates']} coordonnees")
            logger.info(f"  - {transform_stats['coordinates_with_pano']} avec panoId")

            logger.info("\n[3/5] Validation...")
            is_valid, _messages = self.validator.validate_map_data(map_data)

            if not is_valid:
                logger.error("Validation echouee")
                return False

            logger.info("\n[4/5] Sauvegarde...")
            if self.dry_run:
                logger.warning("DRY_RUN: Les fichiers ne seront pas modifies")
            else:
                self._save_output(map_data)
                self._generate_diff(previous_map_data, map_data)

            if self.auto_upload and self.uploader:
                logger.info("\n[5/5] Upload vers map-making.app...")

                if self.dry_run:
                    logger.warning("DRY_RUN: Upload non execute")
                else:
                    upload_map_id = self.map_id or self._prompt_for_map_id()
                    if upload_map_id:
                        success = self.uploader.upload_map_data(map_data, upload_map_id)
                        if not success:
                            logger.warning("Upload echoue, mais pipeline reussie")
                    else:
                        logger.info("Upload annule")

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE REUSSIE")
            logger.info(f"  Duree: {elapsed:.2f}s")
            logger.info(f"  Coordonnees: {transform_stats['total_coordinates']}")
            logger.info(f"  Fichier: {self.output}")
            logger.info("=" * 60)

            return True

        except Exception as exc:
            logger.error(f"ERREUR: {exc}", exc_info=True)
            return False

    def _save_output(self, map_data) -> None:
        """Save transformed data to disk."""
        try:
            self.output.parent.mkdir(parents=True, exist_ok=True)

            with open(self.output, "w", encoding="utf-8") as file_handle:
                payload = (
                    map_data.to_storage_format()
                    if hasattr(map_data, "to_storage_format")
                    else (
                        map_data.model_dump()
                        if hasattr(map_data, "model_dump")
                        else map_data.dict()
                    )
                )
                json.dump(
                    payload,
                    file_handle,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            logger.info(f"Fichier sauvegarde: {self.output}")

        except Exception as exc:
            logger.error(f"Erreur lors de la sauvegarde: {exc}")
            raise

    def _load_previous_output(self) -> Optional[Any]:
        """Load the previous output version before overwriting it."""
        if not self.output.exists():
            return None

        try:
            with open(self.output, "r", encoding="utf-8") as file_handle:
                previous_data_dict = json.load(file_handle)

            from models import MapData as ModelMapData

            return ModelMapData(**previous_data_dict)
        except Exception as exc:
            logger.warning(f"Impossible de charger la version precedente: {exc}")
            return None

    def _generate_diff(self, previous_map_data, map_data) -> None:
        """Generate a diff report against the previous output."""
        try:
            if not previous_map_data:
                logger.info("Aucune version precedente trouvee (premiere execution)")
                return

            diff_data = self.diff_manager.compare_data(previous_map_data, map_data)
            self.diff_manager.print_diff_summary(diff_data)
            self.diff_manager.save_diff_report(diff_data)

        except FileNotFoundError:
            logger.info("Aucune version precedente trouvee (premiere execution)")
        except Exception as exc:
            logger.warning(f"Impossible de generer le diff: {exc}")

    def _prompt_for_map_id(self) -> Optional[str]:
        """Map id must be provided in headless mode."""
        if self.uploader:
            raise NotImplementedError("Interactive prompt non implemente en mode headless")
        return None

    @staticmethod
    def _coordinate_signature(coordinate) -> Tuple[Any, ...]:
        """Build a stable signature for matching equivalent coordinates across runs."""
        return (
            round(coordinate.lat, 7),
            round(coordinate.lng, 7),
            coordinate.panoId or "",
            coordinate.countryCode or "",
            coordinate.stateCode or "",
            tuple(sorted(coordinate.extra.tags)),
        )

    def _preserve_existing_created_at(self, previous_map_data, map_data) -> None:
        """Reuse createdAt from the previous output when the logical coordinate is unchanged."""
        if not previous_map_data:
            return

        existing_created_at: Dict[Tuple[Any, ...], Deque[str]] = defaultdict(deque)
        for coordinate in previous_map_data.customCoordinates:
            if coordinate.createdAt:
                signature = self._coordinate_signature(coordinate)
                existing_created_at[signature].append(coordinate.createdAt)

        reused_count = 0
        for coordinate in map_data.customCoordinates:
            signature = self._coordinate_signature(coordinate)
            if existing_created_at[signature]:
                coordinate.createdAt = existing_created_at[signature].popleft()
                reused_count += 1

        if reused_count:
            logger.info(f"createdAt preserves depuis la sortie precedente: {reused_count}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Pipeline de transformation coordinatesAllTags.json vers map-making.app"
    )

    parser.add_argument(
        "--source",
        choices=["local", "remote", "auto"],
        default="auto",
        help="Source des donnees (defaut: auto)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help=f"Fichier de sortie (defaut: {OUTPUT_FILE})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Cle API map-making.app",
    )
    parser.add_argument(
        "--map-id",
        type=str,
        help="ID de la map map-making.app pour upload",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload vers map-making.app apres transformation",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Mode watch: re-executer si changement detecte",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne pas modifier les fichiers (test only)",
    )

    args = parser.parse_args()

    pipeline = Pipeline(
        source=args.source,
        output=args.output,
        api_key=args.api_key,
        map_id=args.map_id,
        auto_upload=args.upload,
        dry_run=args.dry_run,
    )

    if args.watch:
        logger.info(f"Mode watch active (debounce: {WATCH_DEBOUNCE_SECONDS}s)")

        watcher = Watcher(
            SOURCE_FILE_LOCAL,
            callback=lambda: pipeline.run(),
            debounce_seconds=WATCH_DEBOUNCE_SECONDS,
            ignored_paths=[OUTPUT_FILE, LOG_DIR, BACKUP_DIR],
        )

        pipeline.run()

        try:
            watcher.start()
        except KeyboardInterrupt:
            logger.info("Arret de la pipeline")
    else:
        success = pipeline.run()
        raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
