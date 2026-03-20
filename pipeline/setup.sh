#!/bin/bash
# Setup script pour la pipeline La Ligue
# Usage: bash setup.sh

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  Pipeline La Ligue - Setup Initial"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Détecter le système
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "🔍 Détection du système: $OS"
echo ""

# Vérifier Python
echo "✓ Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "  Python version: $PYTHON_VERSION"

# Créer venv
echo ""
echo "✓ Création de l'environnement virtuel..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  venv créé"
else
    echo "  venv existe déjà"
fi

# Activer venv
if [ "$OS" = "windows" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "  venv activé"

# Installer les dépendances
echo ""
echo "✓ Installation des dépendances..."
pip install --upgrade pip setuptools wheel > /dev/null
pip install -r requirements.txt > /dev/null
echo "  dépendances installées"

# Créer les répertoires
echo ""
echo "✓ Création des répertoires..."
mkdir -p data logs backups
echo "  répertoires créés"

# Setup .env
echo ""
echo "✓ Configuration (.env)..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  .env créé (éditer pour ajouter votre API key)"
else
    echo "  .env existe déjà"
fi

# Test
echo ""
echo "✓ Test d'importation..."
python3 -c "from main import Pipeline; print('  ✓ Import réussi')" 2>/dev/null || echo "  ⚠ Erreur d'import (voir les logs)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ Setup complété!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Prochaines étapes:"
echo "  1. Éditer .env avec votre API key map-making.app"
echo "  2. Lancer: python3 main.py --help"
echo "  3. Exécution unique: python3 main.py"
echo "  4. Mode watch: python3 main.py --watch"
echo ""
echo "Pour Raspberry:"
echo "  1. sudo cp pipeline.service /etc/systemd/system/"
echo "  2. sudo systemctl daemon-reload"
echo "  3. sudo systemctl enable pipeline"
echo "  4. sudo systemctl start pipeline"
echo ""
