@echo off
rem One-time setup on a new Windows machine: creates the Python environment, installs the
rem packages (offline from the bundled "wheels" folder when present), installs Ganache and
rem checks that the trained models load. Afterwards run start.bat.
title AI Fake News Detection - setup
cd /d "%~dp0"
echo ==========================================================
echo   AI Fake News Detection - one-time setup
echo ==========================================================
echo.

echo [1/6] Looking for Python 3.10 or newer...
set "PY="
py -3.12 -c "import sys" >nul 2>nul && set "PY=py -3.12"
if not defined PY py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
if not defined PY goto :no_python
%PY% --version

echo [2/6] Looking for Node.js...
where node >nul 2>nul || goto :no_node
node --version

echo [3/6] Creating the Python virtual environment...
if exist ".venv\Scripts\python.exe" goto :venv_ready
%PY% -m venv .venv || goto :fail
:venv_ready
set "VPY=.venv\Scripts\python.exe"

echo [4/6] Installing Python packages...
if not exist "wheels\" goto :online
"%VPY%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" || goto :online
echo       Using the bundled wheels folder - no internet needed.
"%VPY%" -m pip install --no-index --find-links wheels -r requirements.txt || goto :fail
goto :packages_done
:online
echo       Downloading from the internet - about 1 GB, this can take a while.
"%VPY%" -m pip install --upgrade pip || goto :fail
"%VPY%" -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu || goto :fail
"%VPY%" -m pip install -r requirements.txt || goto :fail
:packages_done

echo [5/6] Installing Ganache - local Ethereum node...
if exist "blockchain\node_modules\" goto :ganache_ready
pushd blockchain
call npm install --no-audit --no-fund
if errorlevel 1 (
  popd
  goto :fail
)
popd
:ganache_ready

echo [6/6] Checking NLTK data and the trained AI models...
"%VPY%" -c "from ml.preprocessing import ensure_nltk_resources; ensure_nltk_resources()" || goto :fail
if not exist "models\metrics.json" goto :no_models
"%VPY%" -c "from ml.predictor import Predictor; p = Predictor(); r = p.predict('Scientists say this setup check headline is working'); print('      Models ready:', ', '.join(p.available_models)); print('      Test prediction:', r['label'], r['confidence'], 'by', r['model'])" || goto :fail

echo.
echo ==========================================================
echo   Setup complete. Double-click start.bat to run the app.
echo ==========================================================
pause
exit /b 0

:no_python
echo.
echo Python 3.10+ was not found.
echo Install Python 3.12 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" in the installer, then run setup.bat again.
pause
exit /b 1

:no_node
echo.
echo Node.js was not found. Install the LTS version from https://nodejs.org
echo then run setup.bat again.
pause
exit /b 1

:no_models
echo.
echo The trained models were not found in the "models" folder.
echo Copy the models folder from the backup, or train them: see RUN_GUIDE.html.
pause
exit /b 1

:fail
echo.
echo Setup failed - read the messages above. RUN_GUIDE.html has a troubleshooting section.
pause
exit /b 1
