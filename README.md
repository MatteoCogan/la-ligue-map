# La Ligue Map

Depot pour la pipeline de transformation et d'upload de la map La Ligue vers `map-making.app`.
Le projet contient aussi un builder leger pour generer des sous-maps GeoGuessr a partir du JSON produit par la pipeline.

## Contenu

- `pipeline/` : code Python, scripts de setup et documentation technique
- `data/` : fichiers source et sortie generes localement
- `logs/` : logs d'execution
- `backups/` : rapports de diff et backups locaux

## Demarrage rapide

```powershell
cd pipeline
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py --source auto --dry-run
```

Sous macOS ou Linux :

```bash
cd pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 main.py --source auto --dry-run
```

## Ce qui est versionne

Le depot est configure pour versionner le code et la documentation, mais pas :

- `pipeline/.env`
- `logs/`
- `backups/`
- les fichiers JSON telecharges ou generes dans `data/`

Les fichiers ignores sont recrees automatiquement au runtime ou telecharges par la pipeline.

## Documentation

La documentation detaillee est dans [pipeline/README.md](pipeline/README.md), [pipeline/QUICK_START.md](pipeline/QUICK_START.md) et [pipeline/MAP_BUILDER.md](pipeline/MAP_BUILDER.md).
