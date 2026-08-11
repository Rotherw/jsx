@echo off
REM ============================================================
REM  WorkShop3D Publisher - START
REM  Uruchamia obserwowanie folderu i otwiera panel w przegladarce.
REM ============================================================
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher

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

REM The desktop shortcut is also the "open dashboard" button. Always check
REM for the existing background process, including hidden installer/autostart
REM launches. A visible shortcut opens the panel; a hidden launch exits.
powershell -NoProfile -Command ^
  "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5000/' -TimeoutSec 2; if($r.StatusCode -ge 200){exit 0} } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 (
  if /I not "%~1"=="--no-browser" (
    call ".venv\Scripts\python.exe" -c "from workshop3d.browser_open import open_in_chrome; open_in_chrome('http://127.0.0.1:5000/')"
  )
  exit /b 0
)
REM Some older desktop shortcuts kept an obsolete path to app.py in their
REM Arguments field. Ignore that one legacy argument instead of passing it to
REM the new CLI, which would otherwise stop with "unrecognized arguments".
if /I "%~x1"==".py" (
  call ".venv\Scripts\python.exe" -m workshop3d
) else (
  call ".venv\Scripts\python.exe" -m workshop3d %*
)

if errorlevel 1 (
  echo.
  echo   Program zakonczyl sie bledem. Przepisz mi komunikat powyzej.
  echo.
  pause
)
