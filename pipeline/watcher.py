"""
Mode watch pour re-exécuter la pipeline automatiquement.
"""
import time
from pathlib import Path
from typing import Callable, List, Optional
from datetime import datetime, timedelta
from logger import setup_logger

logger = setup_logger(__name__)

# Essayer d'importer watchdog, fallback à un simple polling si indisponible
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog non installé, utilisation du polling à la place")
    
    # Créer une classe de base vide pour quand watchdog n'est pas disponible
    class FileSystemEventHandler:
        """Dummy base class when watchdog is not installed."""
        pass


class FileChangeHandler(FileSystemEventHandler):
    """Handler pour les changements de fichiers (avec watchdog)."""
    
    def __init__(self, callback: Callable, debounce_seconds: float = 5):
        """
        Initialiser le handler.
        
        Args:
            callback: Fonction à appeler quand un changement est détecté
            debounce_seconds: Délai avant d'appeler le callback (évite les appels multiples)
        """
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.last_triggered = None
    
    def on_modified(self, event):
        """Appelé quand un fichier est modifié."""
        if event.is_directory:
            return
        
        # Debounce pour éviter plusieurs appels rapides
        now = datetime.now()
        if self.last_triggered and (now - self.last_triggered).total_seconds() < self.debounce_seconds:
            return
        
        self.last_triggered = now
        logger.info(f"Changement détecté: {event.src_path}")
        self.callback()


class Watcher:
    """Gestionnaire de watch pour les changements de fichiers."""
    
    def __init__(self, target_file: Path, callback: Callable, debounce_seconds: float = 5):
        """
        Initialiser le watcher.
        
        Args:
            target_file: Fichier à surveiller
            callback: Fonction à appeler lors de changements
            debounce_seconds: Délai de debounce
        """
        self.target_file = Path(target_file)
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        self.observer = None
        self.last_modified = self.target_file.stat().st_mtime if self.target_file.exists() else 0
    
    def start(self) -> None:
        """Démarrer la surveillance."""
        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling()
    
    def _start_watchdog(self) -> None:
        """Démarrer avec watchdog (plus efficace)."""
        try:
            logger.info(f"Démarrage du watch (watchdog) sur {self.target_file.parent}")
            
            handler = FileChangeHandler(self.callback, self.debounce_seconds)
            self.observer = Observer()
            self.observer.schedule(
                handler,
                str(self.target_file.parent),
                recursive=False
            )
            self.observer.start()
            
            logger.info("✓ Watch démarré (watchdog)")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Arrêt du watch...")
                self.observer.stop()
                self.observer.join()
        
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du watch: {e}")
            logger.info("Fallback vers le polling...")
            self._start_polling()
    
    def _start_polling(self) -> None:
        """Démarrer avec polling (fallback)."""
        logger.info(f"Démarrage du watch (polling) sur {self.target_file}")
        
        try:
            while True:
                if self.target_file.exists():
                    current_mtime = self.target_file.stat().st_mtime
                    
                    if current_mtime > self.last_modified:
                        logger.info(f"Changement détecté: {self.target_file}")
                        self.last_modified = current_mtime
                        
                        # Debounce
                        time.sleep(self.debounce_seconds)
                        self.callback()
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Arrêt du watch")
    
    def stop(self) -> None:
        """Arrêter la surveillance."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watch arrêté")
