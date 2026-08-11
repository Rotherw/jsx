@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo [1/7] Sprawdzanie Node.js...
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js nie jest zainstalowany. Zainstaluj Node.js LTS i uruchom INSTALL.bat ponownie.
  pause
  exit /b 1
)

echo [2/7] Instalacja Local Publisher Bridge dependencies...
cd /d "%~dp0workshop3d_publisher\local_bridge"
call npm install
if errorlevel 1 goto :fail

echo [3/7] Inicjalizacja bridge config i tokenu...
call npm run init
if errorlevel 1 goto :fail

echo [4/7] Konfiguracja folderu watch...
if not exist "F:\Gotowe do sklepu" (
  echo Domyslny folder F:\Gotowe do sklepu nie istnieje. Wybierz folder.
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Wybierz folder Gotowe do sklepu'; if($d.ShowDialog() -eq 'OK'){ $d.SelectedPath }"`) do set SELECTED_FOLDER=%%i
  if "!SELECTED_FOLDER!"=="" (
    echo Nie wybrano folderu.
    goto :fail
  )
) else (
  set SELECTED_FOLDER=F:\Gotowe do sklepu
)

powershell -NoProfile -Command "$p='%~dp0workshop3d_publisher/local_bridge/runtime/config.json'; $c=Get-Content $p -Raw | ConvertFrom-Json; $c.watchFolder='!SELECTED_FOLDER!'; $c | ConvertTo-Json -Depth 10 | Set-Content $p -Encoding UTF8"
if errorlevel 1 goto :fail

echo [5/7] Build Chrome Extension...
cd /d "%~dp0workshop3d_publisher\chrome_extension"
call npm install
if errorlevel 1 goto :fail
call npm run build
if errorlevel 1 goto :fail

echo [6/7] Start lokalnej uslugi bridge...
cd /d "%~dp0"
call START.bat
if errorlevel 1 goto :fail

echo [7/7] Otwieranie folderu gotowego builda rozszerzenia...
start "" "%~dp0workshop3d_publisher\chrome_extension\build"

echo.
echo GOTOWE. W Chrome: chrome://extensions -> Developer mode -> Load unpacked -> wybierz folder build.
pause
exit /b 0

:fail
echo Wystapil blad podczas instalacji.
pause
exit /b 1
