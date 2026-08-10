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
call ".venv\Scripts\python.exe" -m workshop3d %*

if errorlevel 1 (
  echo.
  echo   Program zakonczyl sie bledem. Przepisz mi komunikat powyzej.
  echo.
  pause
)
