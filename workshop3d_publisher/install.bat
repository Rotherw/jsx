@echo off
REM ============================================================
REM  WorkShop3D Auto Publisher - one-click installer (Windows)
REM  Double-click this once. It installs Python if needed,
REM  sets everything up, makes a desktop shortcut, and starts.
REM ============================================================
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher - instalacja

REM Stop only an older Publisher worker.  Otherwise it would keep port 5000
REM and the freshly installed code would appear not to have changed.
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process ^| Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '-m\s+workshop3d' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 2 >nul

echo ============================================
echo  Instalacja WorkShop3D Publisher
echo ============================================
echo.

echo [1/8] Sprawdzam Pythona...
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

echo [2/8] Tworze srodowisko (.venv)...
if not exist ".venv" python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Nie udalo sie utworzyc srodowiska Python.
  pause & exit /b 1
)

echo [3/8] Instaluje biblioteki (to moze chwile potrwac)...
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Nie udalo sie zainstalowac bibliotek. Sprawdz internet i uruchom ponownie.
  pause & exit /b 1
)
call .venv\Scripts\python -m pip install plyer google-api-python-client google-auth

echo [4/8] Przygotowuje folder wrzutowy i skrot na pulpicie...
REM Google Drive dla komputerow NIE jest instalowany: lustrzenie calej
REM biblioteki modeli na dysk roboczy zapycha maszyne. Obszarem roboczym jest
REM ten lokalny folder; do chmury idzie tylko opublikowana paczka (Nextcloud).
if not exist "Gotowe do sklepu" mkdir "Gotowe do sklepu"
if not exist "Opublikowane" mkdir "Opublikowane"
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'WS3D - wrzuc modele.lnk'));" ^
  "$s.TargetPath='%~dp0Gotowe do sklepu'; $s.Save()" >nul 2>&1
echo     Wrzucasz tutaj: %~dp0Gotowe do sklepu

echo [5/8] Przygotowuje font Uncial Antiqua...
if not exist "assets\fonts\UncialAntiqua-Regular.ttf" (
  powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/google/fonts/main/ofl/uncialantiqua/UncialAntiqua-Regular.ttf' -OutFile 'assets\fonts\UncialAntiqua-Regular.ttf' } catch { exit 0 }"
)

echo [6/8] Przygotowuje konfiguracje...
if not exist "config\config.yaml" (
  copy "config\config.example.yaml" "config\config.yaml" >nul
)
set "PYTHONPATH=%~dp0src"
call .venv\Scripts\python.exe -m workshop3d --configure-zero-touch
if errorlevel 1 (
  echo Nie udalo sie wlaczyc pelnego automatu.
  pause & exit /b 1
)
echo     Wlaczono pelny automat - bez zatwierdzania kazdego produktu.
call .venv\Scripts\python.exe -m workshop3d --prepare-browser
if errorlevel 1 (
  echo Nie udalo sie przygotowac automatycznego polaczenia Chrome.
  pause & exit /b 1
)

echo [7/8] Przygotowuje bezposrednia synchronizacje Nextcloud...
echo     Polaczenie i pierwsza kopia do magazynu rusza automatycznie w tle.

echo [8/8] Tworze skroty na pulpicie i w autostarcie Windows...
set "TARGET=%~dp0run.bat"
set "HIDDEN=%~dp0run_hidden.vbs"
set "SHORTCUT=%USERPROFILE%\Desktop\WorkShop3D Publisher.lnk"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WorkShop3D Publisher.lnk"
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%TARGET%'; $s.Arguments=''; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()" >nul 2>&1
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%');" ^
  "$s.TargetPath='%SystemRoot%\System32\wscript.exe'; $s.Arguments=([char]34+'%HIDDEN%'+[char]34); $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()" >nul 2>&1

echo.
echo ============================================
echo  Gotowe! Uruchamiam program...
echo  Od kolejnego logowania do Windows program dziala sam w tle.
echo  Skrot "WorkShop3D Publisher" otwiera tylko panel i statystyki.
echo  Foldery, sklepy i kod Chrome sa wpisane automatycznie.
echo  Jesli Nextcloud poprosi o logowanie, zrob to tylko 1 raz.
echo  Potem wrzucasz folder modelu w skrot "WS3D - wrzuc modele".
echo  Reszte robi automat: publikacja, potem Opublikowane i magazyn w chmurze.
echo ============================================
echo.
start "" "%SystemRoot%\System32\wscript.exe" "%~dp0run_hidden.vbs"
timeout /t 5 >nul
call .venv\Scripts\python.exe -c "from workshop3d.browser_open import open_in_chrome; open_in_chrome('http://127.0.0.1:5000/')"
call .venv\Scripts\python.exe -c "from workshop3d.config import Config; from workshop3d.browser_bridge import BrowserBridge; raise SystemExit(0 if BrowserBridge.shared(Config.load()).status()['connected'] else 1)"
if errorlevel 1 (
  start "" "%~dp0browser_extension"
  call .venv\Scripts\python.exe -c "from workshop3d.browser_open import open_in_chrome; open_in_chrome('chrome://extensions')"
)
