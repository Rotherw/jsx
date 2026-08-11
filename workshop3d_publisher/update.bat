@echo off
REM ============================================================
REM  WorkShop3D Publisher - aktualizacja jednym klikiem
REM  Pobiera najnowsza wersje programu z GitHuba i podmienia
REM  TYLKO kod. NIE rusza: config\config.yaml, config\.env,
REM  folderu work\ (historia produktow) ani .venv.
REM ============================================================
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher - aktualizacja

set "BRANCH=main"
set "ZIPURL=https://github.com/Rotherw/jsx/archive/refs/heads/main.zip"
set "TMPD=%TEMP%\w3d_update"

echo Pobieram najnowsza wersje...
if exist "%TMPD%" rmdir /s /q "%TMPD%"
mkdir "%TMPD%"
powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%TMPD%\update.zip'"
if errorlevel 1 (
  echo Nie udalo sie pobrac aktualizacji. Sprawdz internet i sprobuj ponownie.
  pause & exit /b 1
)

echo Rozpakowuje...
powershell -NoProfile -Command "Expand-Archive -Force '%TMPD%\update.zip' '%TMPD%'"

set "SRC="
for /d %%D in ("%TMPD%\jsx-*") do set "SRC=%%D\workshop3d_publisher"
if not defined SRC (
  echo Nie znaleziono plikow programu w pobranej paczce.
  pause & exit /b 1
)

echo Podmieniam kod (konfiguracja, klucze i historia zostaja nietkniete)...
robocopy "%SRC%\src"   "src"   /MIR >nul
robocopy "%SRC%\tests" "tests" /MIR >nul
robocopy "%SRC%\browser_extension" "browser_extension" /MIR >nul
robocopy "%SRC%\assets" "assets" /E >nul
copy /y "%SRC%\README.md" . >nul
copy /y "%SRC%\requirements.txt" . >nul
copy /y "%SRC%\pyproject.toml" . >nul
copy /y "%SRC%\run.bat" . >nul
copy /y "%SRC%\run_hidden.vbs" . >nul
copy /y "%SRC%\install.bat" . >nul
copy /y "%SRC%\autostart_setup.bat" . >nul
copy /y "%SRC%\update.bat" update_new.bat >nul
copy /y "%SRC%\config\config.example.yaml" "config\config.example.yaml" >nul
call autostart_setup.bat /quiet >nul

echo Aktualizuje biblioteki...
if exist ".venv\Scripts\python.exe" (
  call .venv\Scripts\python -m pip install -q -r requirements.txt
)

if not exist "assets\fonts\UncialAntiqua-Regular.ttf" (
  powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/google/fonts/main/ofl/uncialantiqua/UncialAntiqua-Regular.ttf' -OutFile 'assets\fonts\UncialAntiqua-Regular.ttf' } catch { exit 0 }"
)

rmdir /s /q "%TMPD%"
echo.
echo ============================================
echo  Zaktualizowano. Twoje ustawienia i historia sa zachowane.
echo  Nowa wersja uruchomi sie sama przy kolejnym logowaniu do Windows.
echo  Aby uruchomic ja teraz, kliknij skrot WorkShop3D Publisher.
echo ============================================
pause
