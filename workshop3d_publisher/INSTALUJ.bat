@echo off
REM ============================================================
REM  WorkShop3D Publisher - INSTALATOR (jeden plik)
REM  Kliknij dwa razy. Sam pobierze program, rozpakuje,
REM  zainstaluje, zrobi skrot na pulpicie i uruchomi.
REM  Niczego nie musisz rozumiec ani wpisywac.
REM ============================================================
setlocal
title WorkShop3D Publisher - instalacja

set "ZIPURL=https://github.com/Rotherw/jsx/archive/refs/heads/main.zip"

REM Gdzie zainstalowac: dysk F: jesli istnieje, inaczej folder uzytkownika.
if exist "F:\" (
  set "DEST=F:\WorkShop3D_Publisher"
) else (
  set "DEST=%USERPROFILE%\WorkShop3D_Publisher"
)

echo.
echo  Instaluje WorkShop3D Publisher do:  %DEST%
echo.

set "TMPD=%TEMP%\w3d_boot"
if exist "%TMPD%" rmdir /s /q "%TMPD%"
mkdir "%TMPD%"

echo [1/3] Pobieram program...
powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%TMPD%\w3d.zip'"
if not exist "%TMPD%\w3d.zip" (
  echo Nie udalo sie pobrac. Sprawdz internet i kliknij plik jeszcze raz.
  pause & exit /b 1
)

echo [2/3] Rozpakowuje...
powershell -NoProfile -Command "Expand-Archive -Force '%TMPD%\w3d.zip' '%TMPD%'"
set "SRC="
for /d %%D in ("%TMPD%\jsx-*") do set "SRC=%%D\workshop3d_publisher"
if not defined SRC (
  echo Blad rozpakowania. Kliknij plik jeszcze raz.
  pause & exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"
robocopy "%SRC%" "%DEST%" /E >nul
rmdir /s /q "%TMPD%"

echo [3/3] Instaluje i uruchamiam...
cd /d "%DEST%"
call install.bat
