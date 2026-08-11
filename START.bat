@echo off
setlocal
cd /d "%~dp0workshop3d_publisher\local_bridge"
if not exist runtime mkdir runtime
if exist runtime\bridge.pid (
  set /p OLD_PID=<runtime\bridge.pid
  powershell -NoProfile -Command "if(Get-Process -Id %OLD_PID% -ErrorAction SilentlyContinue){ exit 0 } else { exit 1 }"
  if not errorlevel 1 (
    echo Bridge juz dziala (PID %OLD_PID%).
    exit /b 0
  )
)

powershell -NoProfile -Command "$wd='%cd%'; $p=Start-Process node -ArgumentList 'src/index.js','start' -WorkingDirectory $wd -WindowStyle Hidden -PassThru; Set-Content -Path (Join-Path $wd 'runtime/bridge.pid') -Value $p.Id -Encoding ASCII"
if errorlevel 1 (
  echo Nie udalo sie uruchomic bridge.
  exit /b 1
)

echo Bridge uruchomiony.
exit /b 0
