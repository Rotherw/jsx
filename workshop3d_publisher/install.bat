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

echo [4/8] Sprawdzam synchronizacje Google Drive...
where winget >nul 2>&1
if not errorlevel 1 (
  winget list -e --id Google.GoogleDrive >nul 2>&1
  if errorlevel 1 (
    echo     Instaluje Google Drive dla komputerow...
    winget install -e --id Google.GoogleDrive --silent --accept-source-agreements --accept-package-agreements
  )
) else (
  echo     Brak winget - pomijam opcjonalna instalacje Google Drive.
)

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

echo [7/8] Lacze folder Nextcloud bezposrednio z chmura...
call .venv\Scripts\python.exe -m workshop3d --connect-nextcloud
if errorlevel 1 (
  echo     Nie potwierdzono polaczenia. Przycisk "Polacz Nextcloud" bedzie w panelu.
)

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
echo  W panelu wejdz w Ustawienia ^> Sparowany Chrome i wykonaj 1 raz instrukcje.
echo  Jesli klient Google lub Nextcloud poprosi o logowanie, zrob to tylko 1 raz.
echo  Potem wrzucasz folder do Google Drive ^> FolderSync ^> Gotowe do sklepu.
echo  Reszte robi automat.
echo ============================================
echo.
start "" "%SystemRoot%\System32\wscript.exe" "%~dp0run_hidden.vbs"
timeout /t 5 >nul
call .venv\Scripts\python.exe -c "from workshop3d.browser_open import open_in_chrome; open_in_chrome('http://127.0.0.1:5000/')"
