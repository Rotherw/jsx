@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

title Generator obrazow - start

REM Wagi modelu (~4GB) i cache Hugging Face laduja w folderze "hf-cache"
REM obok aplikacji, a nie na dysku systemowym (C:).
set "HF_HOME=%~dp0hf-cache"

REM ============================================================
REM  Pierwsze uruchomienie: tworzy folder "env", instaluje
REM  PyTorch z obsluga CUDA (Nvidia) i pozostale pakiety.
REM  Kazde kolejne uruchomienie: od razu startuje aplikacje.
REM ============================================================

if exist "env\Scripts\python.exe" goto :run

echo.
echo  ============================================
echo   PIERWSZE URUCHOMIENIE - konfiguracja srodowiska
echo   (to zdarzy sie tylko raz, zajmie kilka minut)
echo  ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [BLAD] Nie znaleziono Pythona. Zainstaluj go z https://www.python.org/downloads/
    echo        i podczas instalacji zaznacz "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Tworzenie srodowiska wirtualnego w folderze "env"...
python -m venv env
if errorlevel 1 goto :error

echo [2/3] Pobieranie PyTorch w wersji dla rdzeni CUDA (Nvidia)...
env\Scripts\python.exe -m pip install --upgrade pip
env\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 goto :error

echo [3/3] Instalacja pozostalych pakietow...
env\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo  Srodowisko gotowe!
echo.

:run
echo Uruchamianie aplikacji... interfejs otworzy sie w przegladarce.
echo (Przy PIERWSZYM generowaniu obrazu Python pobierze wagi modelu ~4GB - to zajmie chwile.)
echo.
env\Scripts\python.exe app.py
pause
exit /b 0

:error
echo.
echo [BLAD] Instalacja nie powiodla sie. Usun folder "env" i uruchom start.bat ponownie.
pause
exit /b 1
