@echo off
REM ============================================================
REM  WorkShop3D Publisher - START
REM  Uruchamia obserwowanie folderu i otwiera panel w przegladarce.
REM ============================================================
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher

REM The desktop shortcut is also the "open dashboard" button. If the hidden
REM background process already runs, do not start a duplicate instance.
if /I not "%~1"=="--no-browser" (
  powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5000/' -TimeoutSec 2; if($r.StatusCode -ge 200){exit 0} } catch {}; exit 1" >nul 2>&1
  if not errorlevel 1 (
    start "" "http://127.0.0.1:5000/"
    exit /b 0
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Program nie jest jeszcze zainstalowany.
  echo   Kliknij plik  1_ZAINSTALUJ.bat  w folderze nadrzednym,
  echo   albo  install.bat  w tym folderze.
  echo.
  pause
  exit /b 1
)

set "PYTHONPATH=%~dp0src"
call ".venv\Scripts\python.exe" -m workshop3d %*

if errorlevel 1 (
  echo.
  echo   Program zakonczyl sie bledem. Przepisz mi komunikat powyzej.
  echo.
  pause
)
