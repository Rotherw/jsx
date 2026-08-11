@echo off
REM ==================================================================
REM  WorkShop3D Publisher - instalacja / aktualizacja jednym kliknieciem
REM ==================================================================
setlocal EnableExtensions
title WorkShop3D Publisher - instalacja
color 0B

set "SOURCE=%~dp0workshop3d_publisher"
if not exist "%SOURCE%\src\workshop3d" goto :not_extracted

REM Reuse the directory behind the existing desktop shortcut.  This keeps the
REM Nextcloud authorization, publication history and browser pairing during an
REM update from a newly downloaded ZIP.
set "DEST="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command ^
  "$d=[Environment]::GetFolderPath('Desktop'); $l=Join-Path $d 'WorkShop3D Publisher.lnk'; if(Test-Path $l){$t=(New-Object -ComObject WScript.Shell).CreateShortcut($l).TargetPath; $p=Split-Path $t; if((Split-Path $t -Leaf) -ieq 'run.bat' -and (Test-Path (Join-Path $p 'src\workshop3d'))){$p}}"`) do set "DEST=%%I"

if not defined DEST (
  if exist "F:\" (
    set "DEST=F:\WorkShop3D_Publisher"
  ) else (
    set "DEST=%LOCALAPPDATA%\WorkShop3D_Publisher"
  )
)

echo.
echo   ==============================================
echo    WorkShop3D Publisher
echo   ==============================================
echo.
echo   Instaluje i zachowuje dotychczasowe polaczenia.
echo   Folder docelowy: %DEST%
echo.

if /I "%SOURCE%"=="%DEST%" goto :install
if not exist "%DEST%" mkdir "%DEST%"

REM Copy application code only.  Never overwrite local credentials, config,
REM work queue or virtual environment already present at the destination.
robocopy "%SOURCE%" "%DEST%" /E /R:2 /W:1 ^
  /XD ".venv" "work" "__pycache__" ".pytest_cache" ^
  /XF "config.yaml" ".env" >nul
if errorlevel 8 goto :copy_failed

:install
cd /d "%DEST%"
call install.bat
exit /b %errorlevel%

:not_extracted
echo.
echo   Najpierw kliknij pobrany ZIP prawym przyciskiem,
echo   wybierz "Wyodrebnij wszystkie", a potem kliknij ten plik ponownie.
echo.
pause
exit /b 1

:copy_failed
echo.
echo   Nie udalo sie zaktualizowac programu. Zamknij jego okno i kliknij
echo   1_ZAINSTALUJ jeszcze raz.
echo.
pause
exit /b 1
