@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo    Установка SpeechEQ
echo ==========================================
echo.

:: Определяем директорию скрипта
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo  Текущая директория: %cd%
echo.

:: Проверка Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python не установлен.
    echo     Установите Python с https://www.python.org/downloads/
    echo     В процессе установки ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH"
    pause
    exit /b 1
)

:: Получаем версию Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo  Версия Python: %PYTHON_VERSION%
echo.

:: Создание виртуального окружения
if exist "venv" (
    echo  Удаление старого виртуального окружения...
    rmdir /s /q venv
)
echo  Создание виртуального окружения...
python -m venv venv
if %errorlevel% neq 0 (
    echo [X] Ошибка создания виртуального окружения
    pause
    exit /b 1
)
echo.

:: Установка зависимостей
echo  Установка Python зависимостей...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel

:: Установка пакетов
python -m pip install numpy>=1.21.0 librosa>=0.10.0 tqdm>=4.65.0 psutil>=5.9.0 soundfile>=0.12.0 PySide6==6.10.0 grpcio>=1.50.0 grpcio-tools>=1.50.0 protobuf>=4.21.0 torch>=2.0.0 scipy>=1.10.0 pyloudnorm>=0.1.1 noisereduce>=3.0.0 speechbrain>=0.5.15 einops>=0.7.0 rotary-embedding-torch>=0.3.0 packaging>=23.0

echo.
echo ==========================================
echo    Установка завершена!
echo ==========================================
echo.
echo  Активировать окружение:
echo    venv\Scripts\activate
echo.
echo  Запуск клиента:
echo    run_app.bat
echo.
echo  Запуск сервера:
echo    run_server.bat
echo.
echo  Деактивация окружения:
echo    deactivate
echo.
echo ==========================================
pause