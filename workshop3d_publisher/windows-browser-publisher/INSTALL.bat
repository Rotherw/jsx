@echo off
setlocal
cd /d "%~dp0"
title WorkShop3D Publisher - INSTALL

echo [1/7] Sprawdzam Node.js...
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js nie jest zainstalowany. Zainstaluj Node.js LTS i uruchom ponownie INSTALL.bat
  pause
  exit /b 1
)

echo [2/7] Instaluję dependencies...
call npm install
if errorlevel 1 goto :fail

echo [3/7] Buduję rozszerzenie...
call npm run build:extension
if errorlevel 1 goto :fail

echo [4/7] Instaluję Local Publisher Bridge...
call npm run install:bridge
if errorlevel 1 goto :fail

echo [5/7] Tworzę config...
if not exist "config\config.json" (
  copy "config\config.example.json" "config\config.json" >nul
)

echo [6/7] Uruchamiam usługę bridge...
start "W3D Bridge" /min cmd /c "cd /d %~dp0 && node bridge\src\index.js"

echo [7/7] Otwieram folder build rozszerzenia...
explorer "%~dp0extension\build"

echo.
echo GOTOWE.
echo 1) Otwórz chrome://extensions
echo 2) Włącz Tryb deweloperski
echo 3) Załaduj folder: %~dp0extension\build
echo.
pause
exit /b 0

:fail
echo Instalacja nieudana.
pause
exit /b 1
