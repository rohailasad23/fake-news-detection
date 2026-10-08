@echo off
rem One-click launcher (Windows): starts the local Ethereum node and the web app,
rem then opens the browser once the app is ready. Close the two windows to stop.
title AI Fake News Detection - launcher
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Follow the setup steps in README.md first.
  pause
  exit /b 1
)
if not exist "blockchain\node_modules" (
  echo Installing Ganache ^(first run only^)...
  pushd blockchain
  call npm install --no-audit --no-fund
  popd
)

echo [1/3] Starting the local Ethereum blockchain (Ganache)...
start "Ganache - Ethereum node" /min cmd /k "cd /d "%~dp0blockchain" && npm run chain"
powershell -NoProfile -Command "for ($i = 0; $i -lt 60; $i++) { if (Test-NetConnection 127.0.0.1 -Port 8545 -InformationLevel Quiet -WarningAction SilentlyContinue) { exit 0 }; Start-Sleep 1 }; exit 1"
if errorlevel 1 echo Warning: Ganache did not respond yet - the app will retry when it is used.

echo [2/3] Starting the web app...
start "Fake News Detection - web app" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0app.py""
powershell -NoProfile -Command "for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/api/status -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep 1 } }; exit 1"
if errorlevel 1 (
  echo The web app did not start. Check the "web app" window for errors.
  pause
  exit /b 1
)

echo [3/3] Opening http://127.0.0.1:5000 ...
start "" http://127.0.0.1:5000
echo.
echo Running. To stop, close the "Ganache" and "web app" windows.
powershell -NoProfile -Command "Start-Sleep 5"
