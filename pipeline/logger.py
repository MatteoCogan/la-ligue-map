"""
Configuration du logging pour la pipeline.
"""
import logging
import logging.handlers
from pathlib import Path
from config import LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Setup un logger avec rotation des fichiers.
    
    Args:
        name: Nom du logger
        
    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Créer le formateur
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Handler de fichier avec rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler de console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Logger principal de l'application
logger = setup_logger("pipeline")
