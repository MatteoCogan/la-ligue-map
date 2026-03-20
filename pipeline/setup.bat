@echo off
REM Setup script pour Windows
REM Utilisation: setup.bat

setlocal enabledelayedexpansion

echo.
echo ===============================================================
echo   Pipeline La Ligue - Setup Initial (Windows)
echo ===============================================================
echo.

REM Verifier Python
echo Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Erreur: Python not found
    echo Telecharger depuis https://www.python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   Python version: %PYTHON_VERSION%
echo.

REM Creer venv
echo Cration de l'environnement virtuel...
if not exist "venv" (
    python -m venv venv
    echo   venv cree
) else (
    echo   venv existe deja
)

REM Activer venv
call venv\Scripts\activate.bat

echo   venv active
echo.

REM Installer les dependances
echo Installation des dependances...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
echo   dependances installees
echo.

REM Creer les repertoires
echo Creation des repertoires...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
echo   repertoires crees
echo.

REM Setup .env
echo Configuration (.env)...
if not exist ".env" (
    copy .env.example .env >nul
    echo   .env cree (editer pour ajouter votre API key)
) else (
    echo   .env existe deja
)
echo.

REM Test import
echo Test d'importation...
python -c "from main import Pipeline; print('  Import reussi')" >nul 2>&1
if errorlevel 1 (
    echo   Avertissement: erreur d'import
) else (
    echo   Import reussi
)
echo.

echo ===============================================================
echo   Setup complete!
echo ===============================================================
echo.
echo Prochaines etapes:
echo   1. Editer .env avec votre API key map-making.app
echo   2. Executer: python main.py --help
echo   3. Execution unique: python main.py
echo   4. Mode watch: python main.py --watch
echo.

pause
