"""
Configuration centralisée de la pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables du .env
load_dotenv()

# Répertoires
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backups"

# S'assurer que les répertoires existent
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# Fichiers
SOURCE_FILE_LOCAL = DATA_DIR / "coordinatesAllTags.json"
SOURCE_FILE_CACTUS = DATA_DIR / "coordinatesCactusTags.json"
OUTPUT_FILE = DATA_DIR / "La ligue.json"
LOG_FILE = LOG_DIR / "pipeline.log"

# URLs
SOURCE_URL = "https://www.laliguegeoguessr.fr/tools/coordinatesAllTags.json"
SOURCE_URL_CACTUS = "https://www.laliguegeoguessr.fr/tools/coordinatesCactusTags.json"
MAP_MAKING_APP_BASE_URL = "https://map-making.app"

# API map-making.app
API_KEY = os.getenv("MMA_API_KEY", "")
MMA_ENDPOINTS = {
    "user": "/api/user",
    "maps": "/api/maps",
    "map_detail": "/api/maps/{mapId}",
    "locations_get": "/api/maps/{mapId}/locations",
    "locations_import": "/api/maps/{mapId}/locations",
}

# Configuration du logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Configuration du watch
WATCH_ENABLED = os.getenv("WATCH_ENABLED", "false").lower() == "true"
WATCH_DEBOUNCE_SECONDS = int(os.getenv("WATCH_DEBOUNCE_SECONDS", "5"))

# Configuration du téléchargement
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))
DOWNLOAD_RETRIES = int(os.getenv("DOWNLOAD_RETRIES", "3"))

# Validation
VALIDATE_COORDINATES = os.getenv("VALIDATE_COORDINATES", "true").lower() == "true"
SKIP_DUPLICATES = os.getenv("SKIP_DUPLICATES", "true").lower() == "true"

# Upload
AUTO_UPLOAD = os.getenv("AUTO_UPLOAD", "false").lower() == "true"
MAP_ID = os.getenv("MMA_MAP_ID", "")  # ID de la map map-making.app à mettre à jour

# Flags supplémentaires
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"
