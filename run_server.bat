@echo off
setlocal

echo ==========================================
echo    Запуск сервера SpeechEQ
echo ==========================================
echo.

:: Определяем директорию скрипта
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Проверяем наличие виртуального окружения
if not exist "venv\" (
    echo [X] Виртуальное окружение не найдено.
    echo     Сначала выполните: install.bat
    pause
    exit /b 1
)

:: Активируем окружение и запускаем сервер с переданными аргументами
call venv\Scripts\activate.bat
python -m src.server.main %*

:: Если сервер завершился, ждём нажатия клавиши перед закрытием окна
pause