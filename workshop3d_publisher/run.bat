@echo off
REM ============================================================
REM  WorkShop3D Auto Publisher - start (Windows)
REM  Double-click this. It starts the folder watcher and opens
REM  the local dashboard in your browser.
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Not installed yet. Please run install.bat first.
  pause
  exit /b 1
)

set PYTHONPATH=%~dp0src
call .venv\Scripts\python -m workshop3d %*
pause
