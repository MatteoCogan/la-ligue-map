# 🚀 Quick Start

## 30 secondes pour démarrer

### Windows

```bash
# Télécharger le dossier pipeline
# Double-cliquer setup.bat

# Ensuite
python main.py
```

### Mac/Linux

```bash
# Télécharger le dossier pipeline
cd pipeline

# Setup
bash setup.sh

# Ensuite
python3 main.py
```

### Raspberry Pi

```bash
# SSH
ssh pi@raspberrypi.local

# Setup
cd /home/pi
git clone <repo>
cd pipeline
bash setup.sh

# Configuration
nano .env
# Ajouter: MMA_API_KEY=votre_clé
# Sauvegarder: Ctrl+X, Y, Enter

# Démarrer le service
sudo cp pipeline.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pipeline
sudo systemctl start pipeline

# Vérifier
sudo journalctl -u pipeline -f
```

---

## Commandes principales

```bash
# Exécution unique
python3 main.py

# Mode watch (ré-exécute si changement)
python3 main.py --watch

# Depuis URL remote
python3 main.py --source remote

# Uploader vers map-making.app
python3 main.py --upload --api-key YOUR_KEY --map-id MAP_ID

# Test dry-run (ne modifie rien)
python3 main.py --dry-run
```

---

## Obtenir votre API key map-making.app

1. Aller sur https://map-making.app
2. Se connecter
3. Aller sur Settings → API Keys → Créer une clé
4. Copier la clé dans `.env` : `MMA_API_KEY=your_key`

---

## Ça marche?

```bash
# Test de connexion
python3 -c "from uploader import Uploader; u = Uploader('YOUR_KEY'); print('✓ OK' if u.test_connection() else '✗ Failed')"
```

---

## Troubleshooting

| Erreur | Solution |
|--------|----------|
| `ModuleNotFoundError: No module named 'requests'` | `pip install -r requirements.txt` |
| `API key invalid` | Vérifier la clé dans `.env` |
| `Connection refused` | Vérifier la connexion internet |
| `No JSON object` | Le fichier source est corrompu, utiliser `--source remote` |

---

**Besoin d'aide?** Voir `README.md` pour la documentation complète.
