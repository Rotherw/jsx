@echo off
REM ============================================================
REM  WorkShop3D Auto Publisher - one-click installer (Windows)
REM  Double-click this once. It installs Python if needed,
REM  sets everything up, makes a desktop shortcut, and starts.
REM ============================================================
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher - instalacja

echo ============================================
echo  Instalacja WorkShop3D Publisher
echo ============================================
echo.

echo [1/6] Sprawdzam Pythona...
python --version >nul 2>&1
if errorlevel 1 (
  echo     Python nie jest zainstalowany. Probuje zainstalowac automatycznie...
  where winget >nul 2>&1
  if errorlevel 1 (
    echo.
    echo     Nie moge zainstalowac automatycznie. Otwieram strone Pythona.
    echo     Zainstaluj Python 3.11+ i ZAZNACZ "Add Python to PATH", potem uruchom install.bat ponownie.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
  )
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  echo     Zamknij to okno i uruchom install.bat jeszcze raz, aby Python zostal wykryty.
  pause
  exit /b 0
)

echo [2/6] Tworze srodowisko (.venv)...
if not exist ".venv" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Nie udalo sie utworzyc srodowiska Python.
  pause & exit /b 1
)

echo [3/6] Instaluje biblioteki (to moze chwile potrwac)...
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Nie udalo sie zainstalowac bibliotek. Sprawdz internet i uruchom ponownie.
  pause & exit /b 1
)
call .venv\Scripts\python -m pip install plyer google-api-python-client google-auth

echo [4/6] Przygotowuje font Uncial Antiqua...
if not exist "assets\fonts\UncialAntiqua-Regular.ttf" (
  powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/google/fonts/main/ofl/uncialantiqua/UncialAntiqua-Regular.ttf' -OutFile 'assets\fonts\UncialAntiqua-Regular.ttf' } catch { exit 0 }"
)

echo [5/6] Przygotowuje konfiguracje...
if not exist "config\config.yaml" (
  copy "config\config.example.yaml" "config\config.yaml" >nul
  echo     Utworzono config\config.yaml ^(tryb testowy DRY_RUN^).
)

echo [6/6] Tworze skrot na pulpicie...
set "TARGET=%~dp0run.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\WorkShop3D Publisher.lnk"
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()" >nul 2>&1

echo.
echo ============================================
echo  Gotowe! Uruchamiam program...
echo  Nastepnym razem klikaj skrot "WorkShop3D Publisher" na pulpicie.
echo  W panelu wejdz w Ustawienia ^> Sparowany Chrome i wykonaj 1 raz instrukcje.
echo ============================================
echo.
start "" "%~dp0run.bat"
timeout /t 3 >nul
