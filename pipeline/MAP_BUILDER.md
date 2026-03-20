# Map Builder

Outil leger pour generer des maps GeoGuessr a partir du JSON deja produit par la pipeline.

## Pourquoi ce choix

Pour un Raspberry Pi Zero 2 W, un CLI/service leger est preferable a un bot Python :

- pas de boucle reseau permanente
- moins de RAM idle
- moins de dependances
- plus simple a lancer via `cron`, `systemd` ou manuellement

Le bon compromis est :

- la logique metier dans `map_builder.py`
- un CLI dans `build_maps.py`
- plus tard, si tu veux, un bot peut simplement appeler ce CLI

## Source utilisee

Par defaut, le builder lit le fichier de sortie de la pipeline :

- `data/La ligue.json`

Ce fichier contient deja les coordonnees au format `map-making.app`, avec les tags enrichis.

## Exemples

Generer une map La Ligue S5 Solo sur le Mexique :

```bash
cd pipeline
python3 build_maps.py \
  --name "La Ligue - S5 Solo Mexique" \
  --source-tag "La Ligue" \
  --season S5 \
  --mode Solo \
  --country Mexique
```

Generer une map Cactus Move et l'uploader :

```bash
cd pipeline
python3 build_maps.py \
  --name "Cactus - Move" \
  --source-tag Cactus \
  --mode Move \
  --upload
```

Generer un sample de 500 locations :

```bash
cd pipeline
python3 build_maps.py \
  --name "La Ligue - France Sample 500" \
  --source-tag "La Ligue" \
  --country France \
  --sample-size 500 \
  --sample-seed 42
```

## Batch mode

Tu peux generer plusieurs maps depuis un seul fichier JSON de spec :

```bash
cd pipeline
python3 build_maps.py --spec-file map_builder.example.json
```

Le fichier d'exemple est :

- `pipeline/map_builder.example.json`

## Filtres disponibles

- `--source-tag` : source exacte, par exemple `La Ligue` ou `Cactus`
- `--season` : tag exact de saison, par exemple `S5`
- `--division` : tag exact de division, par exemple `L1`
- `--journey` : tag exact de journee, par exemple `J3`
- `--mode` : `Solo`, `Coop`, `Move`, `NM`, `NMPZ`, etc.
- `--country` : recherche texte dans les tags, utile pour `France`, `Mexique`, etc.
- `--country-code` : filtre exact sur `countryCode` si present
- `--state-code` : filtre exact sur `stateCode` si present
- `--include-tag-all` : tous les tags listes doivent etre presents
- `--include-tag-any` : au moins un tag doit etre present
- `--exclude-tag` : exclut les coordonnees contenant ce tag
- `--text` : recherche texte libre dans les tags
- `--link-id` : filtre sur le tag `link=...`
- `--sample-size` : echantillon aleatoire reproductible
- `--limit` : coupe le resultat final

## Upload

Le builder reutilise la meme variable d'environnement que la pipeline :

```env
MMA_API_KEY=...
```

Si `--upload` est active :

- avec `--map-id`, la map existante est remplacee
- sans `--map-id`, une nouvelle map est creee
- les gros imports passent par lots de `500` par defaut

## Raspberry Pi

Pour le Pi Zero 2 W :

- evite de faire tourner un bot en permanence juste pour lancer une generation ponctuelle
- prefere `cron` ou un `systemd timer`
- garde des chunks d'upload modestes, `500` est un bon point de depart
- genere les maps a la demande, pas en boucle
