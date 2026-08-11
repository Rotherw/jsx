@echo off
REM ==================================================================
REM  WorkShop3D Publisher - INSTALACJA JEDNYM KLIKNIECIEM
REM
REM  Kliknij ten plik dwa razy. Reszta dzieje sie sama:
REM  znajdzie/zainstaluje Pythona, przygotuje program,
REM  zrobi skrot na pulpicie i uruchomi panel w przegladarce.
REM
REM  Nie musisz nic wpisywac ani rozumiec.
REM ==================================================================
setlocal
title WorkShop3D Publisher - instalacja
color 0B

set "APP=%~dp0workshop3d_publisher"

echo.
echo   ==============================================
echo    WorkShop3D Publisher - instalacja
echo   ==============================================
echo.

REM --- Czy paczka zostala wyodrebniona? ---------------------------
if not exist "%APP%\src" (
  echo   Ten plik nie widzi programu obok siebie.
  echo.
  echo   Najpewniej uruchomiles go PROSTO Z PLIKU ZIP.
  echo   Zrob tak:
  echo     1. Kliknij pobrany plik ZIP prawym przyciskiem
  echo     2. Wybierz "Wyodrebnij wszystkie"
  echo     3. Wejdz do wyodrebnionego folderu
  echo     4. Kliknij ten plik jeszcze raz
  echo.
  pause
  exit /b 1
)

REM --- Szukam Pythona --------------------------------------------
echo   [1/6] Szukam Pythona...
set "PY="
call :probe python
if not defined PY call :probe py
if not defined PY call :probe_paths

if not defined PY (
  echo         Python nie jest zainstalowany - instaluje automatycznie.
  echo         To moze potrwac kilka minut, prosze czekac...
  where winget >nul 2>&1
  if errorlevel 1 goto :no_winget
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
  call :probe_paths
  call :probe python
  call :probe py
)

if not defined PY goto :no_python
echo         Znaleziono: %PY%

REM --- Srodowisko ------------------------------------------------
echo   [2/6] Przygotowuje program...
cd /d "%APP%"
if not exist ".venv\Scripts\python.exe" (
  "%PY%" -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Nie udalo sie przygotowac srodowiska. Napisz mi, co widzisz powyzej.
  pause
  exit /b 1
)

echo   [3/6] Instaluje potrzebne dodatki. To trwa 1-3 minuty,
echo         ponizej beda leciec komunikaty - to normalne, czekaj.
echo.
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :no_deps
REM Dodatki opcjonalne - jesli sie nie zainstaluja, program dziala dalej.
call ".venv\Scripts\python.exe" -m pip install plyer google-api-python-client google-auth
call ".venv\Scripts\python.exe" -c "import yaml, PIL, flask" >nul 2>&1
if errorlevel 1 goto :no_deps

echo   [4/6] Sprawdzam Google Drive i Nextcloud Desktop...
where winget >nul 2>&1
if not errorlevel 1 (
  winget list -e --id Google.GoogleDrive >nul 2>&1
  if errorlevel 1 (
    echo         Instaluje Google Drive dla komputerow...
    winget install -e --id Google.GoogleDrive --silent --accept-source-agreements --accept-package-agreements
  )
  winget list -e --id Nextcloud.NextcloudDesktop >nul 2>&1
  if errorlevel 1 (
    echo         Instaluje Nextcloud Desktop...
    winget install -e --id Nextcloud.NextcloudDesktop --silent --accept-source-agreements --accept-package-agreements
  )
) else (
  echo         Brak winget - pomijam opcjonalna instalacje klientow chmury.
)

echo   [5/6] Ustawienia startowe...
if not exist "config\config.yaml" (
  copy "config\config.example.yaml" "config\config.yaml" >nul
)
set "PYTHONPATH=%APP%\src"
call ".venv\Scripts\python.exe" -m workshop3d --configure-zero-touch
if errorlevel 1 (
  echo.
  echo   Nie udalo sie wlaczyc pelnego automatu. Napisz mi, co widzisz powyzej.
  pause
  exit /b 1
)
if not exist "assets\fonts\UncialAntiqua-Regular.ttf" (
  powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/google/fonts/main/ofl/uncialantiqua/UncialAntiqua-Regular.ttf' -OutFile 'assets\fonts\UncialAntiqua-Regular.ttf' } catch { exit 0 }"
)

echo   [6/6] Robie skroty na pulpicie i w autostarcie Windows...
powershell -NoProfile -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut([IO.Path]::Combine($w.SpecialFolders('Desktop'),'WorkShop3D Publisher.lnk'));" ^
  "$s.TargetPath='%APP%\run.bat'; $s.WorkingDirectory='%APP%'; $s.WindowStyle=7; $s.Save()" >nul 2>&1
powershell -NoProfile -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut([IO.Path]::Combine($w.SpecialFolders('Startup'),'WorkShop3D Publisher.lnk'));" ^
  "$s.TargetPath='%SystemRoot%\System32\wscript.exe'; $s.Arguments=([char]34+'%APP%\run_hidden.vbs'+[char]34); $s.WorkingDirectory='%APP%'; $s.WindowStyle=7; $s.Save()" >nul 2>&1

echo.
echo   ==============================================
echo    GOTOWE!
echo.
echo    Program uruchamia sie teraz w przegladarce.
echo    Od kolejnego logowania do Windows program dziala sam w tle.
echo    Skrot "WorkShop3D Publisher" otwiera panel i statystyki.
echo.
echo    Gotowy folder produktu wrzucaj do:
echo      Google Drive ^> FolderSync ^> Gotowe do sklepu
echo.
echo    W panelu wejdz w Ustawienia ^> Sparowany Chrome.
echo    Panel pokaze jednorazowa instalacje rozszerzenia.
echo    Jesli Google Drive lub Nextcloud poprosi o logowanie,
echo    zrob to tylko raz. Potem reszte robi automat.
echo   ==============================================
echo.
start "" "%APP%\run.bat"
timeout /t 8 >nul
exit /b 0

REM ================= podprogramy ==================================
:probe
if defined PY goto :eof
%~1 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=%~1"
goto :eof

:probe_paths
if defined PY goto :eof
for %%D in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python311\python.exe"
) do (
  if not defined PY if exist %%D set "PY=%%~D"
)
goto :eof

:no_winget
echo.
echo   Nie moge zainstalowac Pythona automatycznie.
echo   Otwieram strone - zainstaluj Pythona i ZAZNACZ
echo   "Add python.exe to PATH", potem kliknij ten plik ponownie.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:no_python
echo.
echo   Python zostal zainstalowany, ale system jeszcze go nie widzi.
echo   Zamknij to okno i kliknij ten plik JESZCZE RAZ - wtedy zadziala.
pause
exit /b 1

:no_deps
echo.
echo   ==============================================
echo    Nie udalo sie pobrac potrzebnych bibliotek.
echo.
echo    Najczestsza przyczyna: brak internetu albo
echo    blokada antywirusa/firewalla.
echo.
echo    Sprawdz internet i kliknij ten plik ponownie.
echo   ==============================================
echo.
pause
exit /b 1
