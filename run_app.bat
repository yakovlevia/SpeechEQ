@echo off
setlocal

echo ==========================================
echo    Запуск клиента SpeechEQ
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

:: Активируем окружение и запускаем клиент
call venv\Scripts\activate.bat
python -m src.client.main

:: Если клиент завершился, ждём нажатия клавиши перед закрытием окна
pause