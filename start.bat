@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

title Generator obrazow - instalacja i start

REM Wagi modelu i cache Hugging Face zostaja obok aplikacji.
set "HF_HOME=%~dp0hf-cache"
set "ENV_DIR=%~dp0env"
set "ENV_PYTHON=%~dp0env\Scripts\python.exe"
set "READY_FILE=%~dp0env\.generator-ready"
set "SETUP_ONLY=0"
set "FORCE_CPU=0"
set "PY_EXE="
set "PY_ARGS="

if /I "%~1"=="--setup-only" set "SETUP_ONLY=1"
if /I "%~1"=="--setup-only-cpu" (
    set "SETUP_ONLY=1"
    set "FORCE_CPU=1"
)

call :environment_ready
if not errorlevel 1 goto :run

echo.
echo  ========================================================
echo   GENERATOR OBRAZOW - AUTOMATYCZNA INSTALACJA
echo   Niczego nie usuwaj. Program zrobi wszystko sam.
echo  ========================================================
echo.

if exist "%ENV_DIR%" (
    echo [ 5%%] Usuwam tylko niedokonczona instalacje programu...
    rmdir /s /q "%ENV_DIR%"
    if exist "%ENV_DIR%" goto :cannot_clean_env
)

echo [10%%] Sprawdzam zgodna wersje Pythona...
call :find_python

if not defined PY_EXE (
    echo [15%%] Pobieram zgodny Python 3.11 dla tego programu...
    call :install_python
    call :find_python
)

if not defined PY_EXE goto :python_error

echo [25%%] Tworze bezpieczne srodowisko programu...
"%PY_EXE%" %PY_ARGS% -m venv "%ENV_DIR%"
if errorlevel 1 goto :install_error

echo [35%%] Aktualizuje instalator pakietow...
"%ENV_PYTHON%" -m pip install --disable-pip-version-check --progress-bar on --upgrade "pip<27"
if errorlevel 1 goto :install_error

if "%FORCE_CPU%"=="1" goto :install_torch_cpu

echo [45%%] Pobieram silnik obrazu dla karty Nvidia...
"%ENV_PYTHON%" -m pip install --disable-pip-version-check --progress-bar on torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
if not errorlevel 1 goto :torch_ready

echo.
echo [60%%] Wersja Nvidia nie pobrala sie. Probuje tryb zgodny z kazdym komputerem...

:install_torch_cpu
"%ENV_PYTHON%" -m pip install --disable-pip-version-check --progress-bar on torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto :install_error

:torch_ready
echo [75%%] Pobieram pozostale skladniki generatora...
"%ENV_PYTHON%" -m pip install --disable-pip-version-check --progress-bar on -r requirements.txt
if errorlevel 1 goto :install_error

echo [95%%] Sprawdzam, czy wszystko dziala...
"%ENV_PYTHON%" -c "import torch, diffusers, transformers, accelerate, safetensors, gradio"
if errorlevel 1 goto :install_error

>"%READY_FILE%" echo gotowe

echo.
echo  ========================================================
echo   [100%%] GOTOWE
echo  ========================================================
echo.

:run
if "%SETUP_ONLY%"=="1" exit /b 0

echo [100%%] Uruchamiam generator. Strona otworzy sie sama.
echo Przy pierwszym obrazie pobiora sie wagi modelu. Postep bedzie widoczny tutaj.
echo.
"%ENV_PYTHON%" app.py
if errorlevel 1 goto :run_error
pause
exit /b 0

:environment_ready
if not exist "%ENV_PYTHON%" exit /b 1
if not exist "%READY_FILE%" exit /b 1
"%ENV_PYTHON%" -c "import torch, diffusers, transformers, accelerate, safetensors, gradio" >nul 2>nul
exit /b %errorlevel%

:find_python
set "PY_EXE="
set "PY_ARGS="

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" -c "import struct,sys;raise SystemExit(0 if sys.version_info[:2]==(3,11) and struct.calcsize('P')==8 else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
        exit /b 0
    )
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" -c "import struct,sys;raise SystemExit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
        exit /b 0
    )
)

python -c "import struct,sys;raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) and struct.calcsize('P')==8 else 1)" >nul 2>nul
if not errorlevel 1 set "PY_EXE=python"
exit /b 0

:install_python
set "PY_INSTALLER=%TEMP%\workshop3d-python-3.11.9-amd64.exe"

where winget >nul 2>nul
if not errorlevel 1 (
    winget install --id Python.Python.3.11 -e --scope user --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
    call :find_python
    if defined PY_EXE exit /b 0
)

echo       Pobieranie Python 3.11 (okolo 25 MB)...
del /q "%PY_INSTALLER%" >nul 2>nul
where curl.exe >nul 2>nul
if not errorlevel 1 (
    curl.exe -L --fail --progress-bar -o "%PY_INSTALLER%" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile (Join-Path $env:TEMP 'workshop3d-python-3.11.9-amd64.exe')"
)
if errorlevel 1 (
    del /q "%PY_INSTALLER%" >nul 2>nul
    exit /b 1
)
if not exist "%PY_INSTALLER%" exit /b 1

echo       Instalacja Python 3.11 - postep widac w osobnym oknie...
start "" /wait "%PY_INSTALLER%" /passive InstallAllUsers=0 PrependPath=0 Include_launcher=1 InstallLauncherAllUsers=0 Include_test=0 Include_doc=0 Include_dev=0 SimpleInstall=1
del /q "%PY_INSTALLER%" >nul 2>nul
exit /b 0

:cannot_clean_env
echo.
echo [BLAD] Program nie moze odswiezyc swojej niedokonczonej instalacji.
echo Zamknij inne okna Generatora obrazow i kliknij ten plik ponownie.
pause
exit /b 1

:python_error
echo.
echo [BLAD] Nie udalo sie automatycznie zainstalowac zgodnego Pythona.
echo Sprawdz polaczenie z internetem i kliknij ten plik ponownie.
pause
exit /b 1

:install_error
echo.
echo [BLAD] Pobieranie nie zostalo zakonczone.
echo Niczego nie usuwaj. Sprawdz internet i kliknij ten plik ponownie.
echo Program sam naprawi niedokonczona instalacje.
pause
exit /b 1

:run_error
echo.
echo [BLAD] Generator nie wystartowal. Zrob zdjecie tego okna i wyslij je tutaj.
pause
exit /b 1
