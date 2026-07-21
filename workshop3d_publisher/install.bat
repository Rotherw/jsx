@echo off
REM ============================================================
REM  WorkShop3D Auto Publisher - one-time installer (Windows)
REM  Creates a local Python environment and installs everything.
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Please install Python 3.11+ from https://www.python.org/downloads/
  echo During install, tick "Add Python to PATH".
  pause
  exit /b 1
)

echo [2/4] Creating virtual environment (.venv)...
if not exist ".venv" python -m venv .venv

echo [3/4] Installing dependencies...
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\python -m pip install -r requirements.txt
REM Optional extras for Windows toast notifications:
call .venv\Scripts\python -m pip install plyer

echo [4/4] Preparing configuration...
if not exist "config\config.yaml" (
  copy "config\config.example.yaml" "config\config.yaml"
  echo Created config\config.yaml  ^(edit it to set your folders^).
)

echo.
echo Done. Start the program by double-clicking  run.bat
pause
