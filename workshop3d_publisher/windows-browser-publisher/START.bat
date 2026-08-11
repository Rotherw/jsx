@echo off
setlocal
cd /d "%~dp0"

echo Uruchamiam Local Publisher Bridge...
start "W3D Bridge" /min cmd /c "cd /d %~dp0 && node bridge\src\index.js"

echo Otwieram folder build rozszerzenia...
explorer "%~dp0extension\build"

echo Gotowe.
