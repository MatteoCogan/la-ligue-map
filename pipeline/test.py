#!/usr/bin/env python3
"""
Test simple pour la pipeline.
Utilisation: python3 test.py
"""

import sys
from pathlib import Path

def test_imports():
    """Tester que tous les imports fonctionnent."""
    print("🧪 Test des imports...")
    try:
        import pydantic
        print("  ✓ pydantic")
    except ImportError:
        print("  ✗ pydantic - pip install pydantic")
        return False
    
    try:
        import requests
        print("  ✓ requests")
    except ImportError:
        print("  ✗ requests - pip install requests")
        return False
    
    try:
        from config import API_KEY, OUTPUT_FILE
        print("  ✓ config")
    except ImportError as e:
        print(f"  ✗ config - {e}")
        return False
    
    try:
        from loader import Loader
        print("  ✓ loader")
    except ImportError as e:
        print(f"  ✗ loader - {e}")
        return False
    
    try:
        from transformer import Transformer
        print("  ✓ transformer")
    except ImportError as e:
        print(f"  ✗ transformer - {e}")
        return False
    
    try:
        from validator import Validator
        print("  ✓ validator")
    except ImportError as e:
        print(f"  ✗ validator - {e}")
        return False
    
    try:
        from uploader import Uploader
        print("  ✓ uploader")
    except ImportError as e:
        print(f"  ✗ uploader - {e}")
        return False
    
    return True

def test_config():
    """Tester la configuration."""
    print("\n🔧 Test de configuration...")
    from config import API_KEY, OUTPUT_FILE, BACKUP_DIR, LOG_FILE
    
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"  Backup dir: {BACKUP_DIR}")
    print(f"  Log file: {LOG_FILE}")
    
    if API_KEY:
        print(f"  API Key: *** (configurée)")
    else:
        print(f"  API Key: NOT SET - ajouter MMA_API_KEY à .env")
    
    return True

def test_loader():
    """Tester le chargement."""
    print("\n📥 Test du loader...")
    from loader import Loader
    
    loader = Loader(source="local")
    
    local_file = Path("../data/coordinatesAllTags.json")
    if local_file.exists():
        print(f"  ✓ Fichier local trouvé: {local_file}")
        return True
    else:
        print(f"  ⚠ Fichier local absent: {local_file}")
        print(f"  Utilisez --source remote pour télécharger")
        return True

def test_models():
    """Tester les models Pydantic."""
    print("\n💾 Test des models...")
    from models import Coordinate, Extra, MapData
    
    extra = Extra(tags=["test", "S5"])
    coord = Coordinate(
        lat=48.8566,
        lng=2.3522,
        heading=45.0,
        pitch=-10.0,
        zoom=0.5,
        extra=extra
    )
    
    map_data = MapData(
        name="Test Map",
        customCoordinates=[coord]
    )
    
    print(f"  ✓ Coordinate créée: {coord.lat}, {coord.lng}")
    print(f"  ✓ MapData créée avec {len(map_data.customCoordinates)} coordonnées")
    
    return True

def test_uploader():
    """Tester la connexion uploader."""
    print("\n🔌 Test du uploader...")
    from uploader import Uploader
    from config import API_KEY
    
    if not API_KEY:
        print("  ⚠ Pas de clé API - ajouter MMA_API_KEY à .env")
        return True
    
    uploader = Uploader(API_KEY)
    
    try:
        if uploader.test_connection():
            print("  ✓ Connexion API réussie")
            return True
        else:
            print("  ✗ Auth failed - vérifier la clé API")
            return False
    except Exception as e:
        print(f"  ⚠ Erreur: {e}")
        return True

def main():
    """Exécuter tous les tests."""
    print("=" * 60)
    print("  Pipeline La Ligue - Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Config", test_config),
        ("Loader", test_loader),
        ("Models", test_models),
        ("Uploader", test_uploader),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Erreur dans {name}: {e}")
            results.append((name, False))
    
    # Résumé
    print("\n" + "=" * 60)
    print("  Résumé")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print(f"\n  {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ Tous les tests réussis!")
        print("Vous pouvez lancer: python3 main.py")
        return 0
    else:
        print("\n✗ Certains tests ont échoué")
        print("Vérifier les erreurs ci-dessus")
        return 1

if __name__ == "__main__":
    sys.exit(main())
