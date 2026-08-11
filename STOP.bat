@echo off
setlocal
cd /d "%~dp0workshop3d_publisher\local_bridge"
if not exist runtime\bridge.pid (
  echo Brak pliku PID. Bridge prawdopodobnie nie dziala.
  exit /b 0
)
set /p PID=<runtime\bridge.pid
powershell -NoProfile -Command "if(Get-Process -Id %PID% -ErrorAction SilentlyContinue){ Stop-Process -Id %PID% -Force; exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo Proces %PID% nie istnieje.
) else (
  echo Zatrzymano bridge PID %PID%.
)
del /q runtime\bridge.pid >nul 2>&1
exit /b 0
