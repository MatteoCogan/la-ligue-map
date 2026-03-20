# Pipeline La Ligue - Transform & Upload

Pipeline Python pour transformer `coordinatesAllTags.json` et uploader vers `map-making.app`.

## ✨ Fonctionnalités

- ✅ **Chargement** : Local ou remote (avec retry et cache)
- ✅ **Transformation** : Format source → format map-making.app
- ✅ **Validation** : Vérification des coordonnées
- ✅ **Upload API** : Intégration directe map-making.app
- ✅ **Mode Watch** : Re-exécution automatique sur changement
- ✅ **Diff Tracking** : Rapport des changements
- ✅ **Logging** : Logs rotatifs et console
- ✅ **Raspberry Ready** : Systemd service + cron

## 🚀 Démarrage rapide

### Setup local (PC/Mac/Linux)

```bash
# Cloner ou créer le projet
cd pipeline

# Créer venv
python3 -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Éditer .env si nécessaire

# Exécution unique
python3 main.py --source auto

# Mode watch (re-exécute si changement)
python3 main.py --source auto --watch
```

### Setup Raspberry Pi

```bash
# SSH dans Raspberry
ssh pi@raspberrypi.local

# Cloner le projet
cd /home/pi
git clone https://github.com/tumonitor/pipeline.git
cd pipeline

# Setup venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
nano .env  # Ajouter MMA_API_KEY, MMA_MAP_ID, etc.

# Installer le service systemd
sudo cp pipeline.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pipeline
sudo systemctl start pipeline

# Vérifier le statut
sudo systemctl status pipeline

# Logs
sudo journalctl -u pipeline -f  # Suivi en temps réel
sudo journalctl -u pipeline -n 100  # Dernières 100 lignes
```

## 📋 CLI Usage

```bash
# Exécution unique (source auto)
python3 main.py

# Depuis URL remote avec validation strict
python3 main.py --source remote

# Uniquement La Ligue
python3 main.py --source remote --dataset la-ligue

# Uniquement Cactus
python3 main.py --source remote --dataset cactus

# Depuis fichier local
python3 main.py --source local

# Uploader vers map-making.app
python3 main.py --upload --api-key YOUR_API_KEY --map-id MAP_ID

# Re-uploader le JSON final existant sans retraiter les sources
python3 main.py --upload-only --api-key YOUR_API_KEY --map-id MAP_ID

# Invalide: upload-only ne peut pas tourner avec le watch
# python3 main.py --upload-only --watch

# Mode watch (surveillance fichier)
python3 main.py --watch

# Test dry-run (ne modifie rien)
python3 main.py --dry-run

# Tous les paramètres
python3 main.py \
  --source auto \
  --dataset both \
  --output data/La_ligue.json \
  --api-key YOUR_API_KEY \
  --map-id MAP_ID \
  --upload \
  --watch
```

## ⚙️ Configuration (.env)

```env
# API map-making.app (requis pour upload)
MMA_API_KEY=your_api_key_here

# ID de la map à uploader (optionnel, créé nouvelle map sinon)
MMA_MAP_ID=optional_map_id

# Source: local | remote | auto (défaut)
SOURCE=auto

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Mode watch
WATCH_ENABLED=false
WATCH_DEBOUNCE_SECONDS=5

# Traitement
VALIDATE_COORDINATES=true
SKIP_DUPLICATES=true

# Features
AUTO_UPLOAD=false
DRY_RUN=false
VERBOSE=false

# Timeouts
DOWNLOAD_TIMEOUT=30
DOWNLOAD_RETRIES=3
```

## 📂 Structure

```
pipeline/
├── main.py              # CLI principal + orchestrateur
├── loader.py            # Chargement (local/remote)
├── transformer.py       # Transformation des données
├── validator.py         # Validation
├── uploader.py          # Upload API map-making.app
├── watcher.py           # Mode watch
├── diff.py              # Gestion des diffs
├── models.py            # Pydantic models
├── logger.py            # Configuration logging
├── config.py            # Constantes et config
├── requirements.txt     # Dépendances
├── .env.example         # Template config
├── pipeline.service     # Systemd service (Raspberry)
├── README.md            # Cette doc
├── data/                # Données (*.json)
├── logs/                # Logs rotatifs
└── backups/             # Backups et diffs
```

## 🔗 API map-making.app (Intégration)

### Endpoints utilisés

```
POST   https://map-making.app/api/maps                      # Créer map
GET    https://map-making.app/api/maps                      # Lister maps
GET    https://map-making.app/api/maps/{mapId}              # Détail map
PUT    https://map-making.app/api/maps/{mapId}              # Mettre à jour
GET    https://map-making.app/api/maps/{mapId}/locations    # Get locations
POST   https://map-making.app/api/maps/{mapId}/locations    # Import locations
GET    https://map-making.app/api/user                      # Auth check
```

### Authentification

```
Header: Authorization: API {api_key}
Content-Type: application/json
```

### Format d'import

```json
{
  "edits": [{
    "action": {"type": 4},
    "create": [
      {
        "id": -1,
        "flags": 0,
        "location": {"lat": 48.8566, "lng": 2.3522},
        "panoId": null,
        "heading": 45.0,
        "pitch": -10.0,
        "zoom": 0.5,
        "tags": ["S5", "J0", "Solo", "Move", "link=xyz..."],
        "createdAt": "2026-03-19T16:30:00.000Z"
      }
    ],
    "remove": []
  }]
}
```

## 📊 Exemple d'exécution

```
$ python3 main.py --source remote --upload --api-key xxx

============================================================
DÉBUT DE LA PIPELINE
============================================================

[1/5] Chargement des données...
INFO: Chargement depuis URL remote
INFO: Chargé 3717 items depuis URL remote
INFO: Cache local sauvegardé dans /home/pi/pipeline/data/coordinatesAllTags.json
INFO: Structure validée: 3717 items avec les bonnes clés

[2/5] Transformation...
INFO: Début de la transformation de 3717 items
INFO: Transformation complétée: 15000 coordonnées transformées, 50 doublons ignorés, 0 erreurs
  - 15000 coordonnées
  - 2000 avec panoId
  - 0 doublons ignorés

[3/5] Validation...
INFO: Début de la validation
INFO: Validation réussie: 15000 coordonnées valides

[4/5] Sauvegarde...
INFO: Fichier sauvegardé: /home/pi/pipeline/data/La ligue.json

[5/5] Upload vers map-making.app...
INFO: Test de connexion à l'API map-making.app...
✓ Connexion réussie! Utilisateur: john_doe
INFO: Import de 15000 coordonnées vers la map 123abc...
✓ 15000 coordonnées importées avec succès
✓ Map complètement uploadée: 123abc

============================================================
✓ PIPELINE RÉUSSIE!
  Durée: 45.23s
  Coordonnées: 15000
  Fichier: /home/pi/pipeline/data/La ligue.json
============================================================
```

## 🛠️ Dépannage

### Erreur: "Clé API invalide"
```bash
# Vérifier la clé API
echo "MMA_API_KEY=..." >> .env

# Tester la connexion
python3 -c "from uploader import Uploader; u = Uploader('YOUR_KEY'); print(u.test_connection())"
```

### Mode watch ne compile pas
```bash
# Watchdog non installé, fallback au polling
pip install watchdog
```

### Erreur de JSON
```bash
# Valider le fichier source
python3 -c "import json; json.load(open('data/coordinatesAllTags.json'))"
```

### Services Raspberry ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u pipeline -n 50

# Tester manuellement
cd /home/pi/pipeline
source venv/bin/activate
python3 main.py --dry-run
```

## 📝 Logs

Les logs sont stockés dans `logs/pipeline.log` avec rotation automatique.

```bash
# Afficher les logs en temps réel
tail -f logs/pipeline.log

# Sous Raspberry (systemd)
sudo journalctl -u pipeline -f
```

## 📦 Packager pour Raspberry

```bash
# Export config de Raspberry
cat > /home/pi/pipeline/.env << EOF
MMA_API_KEY=your_key
MMA_MAP_ID=your_map_id
WATCH_ENABLED=true
AUTO_UPLOAD=true
EOF

# Test du service
sudo systemctl restart pipeline
sudo systemctl status pipeline
```

## 🔄 Mode Cron (alternative au watch)

Au lieu de utiliser le service systemd, on peut utiliser cron sur Raspberry:

```bash
# Éditer le crontab
crontab -e

# Ajouter (exécute toutes les 6 heures)
0 */6 * * * cd /home/pi/pipeline && /home/pi/pipeline/venv/bin/python3 main.py >> logs/cron.log 2>&1

# Ou tous les jours à 3h du matin
0 3 * * * cd /home/pi/pipeline && /home/pi/pipeline/venv/bin/python3 main.py
```

## 🧪 Tests unitaires

```bash
# Exécuter les tests
python3 -m pytest tests/

# Avec coverage
python3 -m pytest --cov=. tests/
```

## 📄 Licence

MIT

## 👥 Contributeurs

- Tu l'es ! 🚀

## ❓ Questions?

Voir `/docs` pour plus de détails.
