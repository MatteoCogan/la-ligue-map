"""
Watch mode utilities for re-running the pipeline on source changes.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional, Set

from logger import setup_logger

logger = setup_logger(__name__)

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog non installe, utilisation du polling a la place")

    class FileSystemEventHandler:
        """Fallback base class when watchdog is unavailable."""

        pass


class FileChangeHandler(FileSystemEventHandler):
    """Watchdog handler that only reacts to the tracked source file."""

    def __init__(
        self,
        target_file: Path,
        callback: Callable[[], None],
        debounce_seconds: float = 5,
        ignored_paths: Optional[Iterable[Path]] = None,
    ):
        self.target_file = Path(target_file).resolve(strict=False)
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.last_triggered: Optional[datetime] = None
        self.ignored_paths: Set[Path] = {
            Path(path).resolve(strict=False) for path in (ignored_paths or [])
        }

    def _should_ignore(self, path: Path) -> bool:
        for ignored_path in self.ignored_paths:
            if path == ignored_path or ignored_path in path.parents:
                return True
        return False

    def _handle_path(self, raw_path: str) -> None:
        event_path = Path(raw_path).resolve(strict=False)

        if self._should_ignore(event_path):
            logger.debug(f"Changement ignore: {event_path}")
            return

        if event_path != self.target_file:
            logger.debug(f"Changement hors cible ignore: {event_path}")
            return

        now = datetime.now()
        if self.last_triggered and (now - self.last_triggered).total_seconds() < self.debounce_seconds:
            return

        self.last_triggered = now
        logger.info(f"Changement detecte sur le fichier source: {event_path}")
        self.callback()

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        self._handle_path(event.src_path)

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self._handle_path(event.src_path)

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        self._handle_path(event.dest_path)


class Watcher:
    """Watch a specific input file and rerun the callback when it changes."""

    def __init__(
        self,
        target_file: Path,
        callback: Callable[[], None],
        debounce_seconds: float = 5,
        ignored_paths: Optional[Iterable[Path]] = None,
    ):
        self.target_file = Path(target_file).resolve(strict=False)
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.ignored_paths: Set[Path] = {
            Path(path).resolve(strict=False) for path in (ignored_paths or [])
        }

        self.observer: Optional[Observer] = None if HAS_WATCHDOG else None
        self.last_modified = self.target_file.stat().st_mtime if self.target_file.exists() else 0.0

    def start(self) -> None:
        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()

    def _start_watchdog(self) -> None:
        try:
            logger.info(f"Demarrage du watch (watchdog) sur {self.target_file.parent}")

            handler = FileChangeHandler(
                target_file=self.target_file,
                callback=self.callback,
                debounce_seconds=self.debounce_seconds,
                ignored_paths=self.ignored_paths,
            )
            self.observer = Observer()
            self.observer.schedule(handler, str(self.target_file.parent), recursive=False)
            self.observer.start()

            logger.info("Watch demarre (watchdog)")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Arret du watch...")
                self.observer.stop()
                self.observer.join()

        except Exception as exc:
            logger.error(f"Erreur lors du demarrage du watch: {exc}")
            logger.info("Fallback vers le polling...")
            self._start_polling()

    def _start_polling(self) -> None:
        logger.info(f"Demarrage du watch (polling) sur {self.target_file}")

        try:
            while True:
                if self.target_file.exists():
                    current_mtime = self.target_file.stat().st_mtime

                    if current_mtime > self.last_modified:
                        logger.info(f"Changement detecte sur le fichier source: {self.target_file}")
                        self.last_modified = current_mtime
                        time.sleep(self.debounce_seconds)
                        self.callback()

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Arret du watch")

    def stop(self) -> None:
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watch arrete")
