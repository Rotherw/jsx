@echo off
REM ==================================================================
REM  Inwentaryzacja maszynerii WorkShop3D na dysku przenosnym.
REM  Skrypt TYLKO CZYTA - niczego nie przenosi ani nie kasuje.
REM  Wynik trafia na Pulpit: WS3D-INWENTARZ.md + ws3d-inwentarz.json
REM ==================================================================
setlocal EnableExtensions
title WorkShop3D - inwentaryzacja dysku
color 0B

echo.
echo   ==============================================
echo    WorkShop3D - inwentaryzacja dysku
echo   ==============================================
echo.
echo   Podepnij dysk przenosny i poczekaj.
echo   Nic nie zostanie zmienione ani skasowane.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0skan-dysku.ps1" %*

echo.
pause
