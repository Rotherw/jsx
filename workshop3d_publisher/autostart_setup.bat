@echo off
REM ============================================================
REM  Add WorkShop3D Auto Publisher to Windows startup.
REM  Creates a hidden background shortcut in the current user's
REM  Startup folder so it launches when Windows starts.
REM ============================================================
setlocal
cd /d "%~dp0"

set "TARGET=%SystemRoot%\System32\wscript.exe"
set "HIDDEN=%~dp0run_hidden.vbs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\WorkShop3D Publisher.lnk"

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.Arguments=([char]34+'%HIDDEN%'+[char]34);" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.WindowStyle=7;" ^
  "$s.Save()"

echo Startup shortcut created:
echo   %SHORTCUT%
echo To remove it later, delete that file.
if /I "%~1"=="/quiet" exit /b 0
pause
