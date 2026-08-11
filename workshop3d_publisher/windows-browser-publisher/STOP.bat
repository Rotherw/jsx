@echo off
setlocal

echo Zatrzymuję proces Node bridge...
for /f "tokens=2" %%A in ('tasklist ^| findstr /i "node.exe"') do (
  taskkill /PID %%A /F >nul 2>&1
)

echo Zatrzymano.
