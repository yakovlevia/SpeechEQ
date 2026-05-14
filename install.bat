@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==========================================
echo        SpeechEQ Installer
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "REQUIRED_VER=3.10.12"

:: =========================
:: LICENSE CHECK
:: =========================

if not exist "LICENSE" (
    echo [X] LICENSE file not found.
    pause
    exit /b 1
)

echo [i] Opening license window...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Add-Type -AssemblyName System.Windows.Forms; ^
Add-Type -AssemblyName System.Drawing; ^
$license = Get-Content 'LICENSE' -Raw; ^
$form = New-Object System.Windows.Forms.Form; ^
$form.Text = 'SpeechEQ License Agreement'; ^
$form.Width = 720; ^
$form.Height = 520; ^
$form.StartPosition = 'CenterScreen'; ^
$form.Font = New-Object System.Drawing.Font('Segoe UI',9); ^
$form.BackColor = [System.Drawing.Color]::White; ^
$text = New-Object System.Windows.Forms.RichTextBox; ^
$text.Dock = 'Fill'; ^
$text.ReadOnly = $true; ^
$text.ScrollBars = 'Vertical'; ^
$text.Text = $license; ^
$text.BackColor = 'White'; ^
$text.BorderStyle = 'None'; ^
$panel = New-Object System.Windows.Forms.Panel; ^
$panel.Dock = 'Bottom'; ^
$panel.Height = 60; ^
$accept = New-Object System.Windows.Forms.Button; ^
$accept.Text = 'Accept'; ^
$accept.Width = 100; ^
$accept.Height = 32; ^
$accept.Left = 480; ^
$accept.Top = 15; ^
$accept.DialogResult = [System.Windows.Forms.DialogResult]::OK; ^
$decline = New-Object System.Windows.Forms.Button; ^
$decline.Text = 'Decline'; ^
$decline.Width = 100; ^
$decline.Height = 32; ^
$decline.Left = 590; ^
$decline.Top = 15; ^
$decline.DialogResult = [System.Windows.Forms.DialogResult]::Cancel; ^
$panel.Controls.Add($accept); ^
$panel.Controls.Add($decline); ^
$form.Controls.Add($text); ^
$form.Controls.Add($panel); ^
$result = $form.ShowDialog(); ^
if ($result -eq 'OK') { exit 0 } else { exit 1 }"

if %errorlevel% neq 0 (
    echo [X] License declined. Installation cancelled.
    pause
    exit /b 1
)

echo [+] License accepted.
echo.

:: =========================
:: FFMPEG CHECK
:: =========================

echo Checking FFmpeg...

where ffmpeg >nul 2>&1

if %errorlevel% neq 0 (
    echo FFmpeg not found.
    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] Winget not available.
        echo     Download FFmpeg manually: https://www.gyan.dev/ffmpeg/builds/
    ) else (
        echo Installing FFmpeg via winget...
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
        if !errorlevel! neq 0 (
            echo [!] FFmpeg installation failed. Please install manually.
        ) else (
            echo [+] FFmpeg installed.
        )
    )
) else (
    echo [+] FFmpeg found.
)

echo.

:: =========================
:: PYTHON 3.10.12 CHECK
:: =========================

echo Checking Python %REQUIRED_VER%...

set "PYTHON_CMD="

:: Ищем Python с точной версией 3.10.12
for /f "tokens=*" %%p in ('where python 2^>nul') do (
    for /f "tokens=2" %%v in ('"%%p" --version 2^>^&1') do (
        if "%%v"=="%REQUIRED_VER%" (
            if not defined PYTHON_CMD set "PYTHON_CMD=%%p"
        )
    )
)

:: Также проверим py launcher
if not defined PYTHON_CMD (
    py -3.10 --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%v in ('py -3.10 --version 2^>^&1') do (
            if "%%v"=="%REQUIRED_VER%" set "PYTHON_CMD=py -3.10"
        )
    )
)

if not defined PYTHON_CMD (
    echo Python %REQUIRED_VER% not found. Installing via winget...
    echo.

    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo [X] Winget not available.
        echo     Download Python %REQUIRED_VER% manually: https://www.python.org/downloads/release/python-31012/
        pause
        exit /b 1
    )

    winget install --id Python.Python.3.10 -e --accept-package-agreements --accept-source-agreements

    if %errorlevel% neq 0 (
        echo [X] Python %REQUIRED_VER% installation failed.
        pause
        exit /b 1
    )

    :: Обновляем PATH для текущей сессии
    set "PY310_PATH=%LOCALAPPDATA%\Programs\Python\Python310"
    set "PATH=%PY310_PATH%;%PY310_PATH%\Scripts;%PATH%"

    set "PYTHON_CMD=python"
)

:: Показываем версию
for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do (
    echo [+] Python: %%v  ^(%PYTHON_CMD%^)
)
echo.

:: Проверяем точную версию
for /f "tokens=2" %%i in ('"%PYTHON_CMD%" --version 2^>^&1') do set PY_VER=%%i
if not "%PY_VER%"=="%REQUIRED_VER%" (
    echo [X] Python %REQUIRED_VER% required, found %PY_VER%.
    echo     Download: https://www.python.org/downloads/release/python-31012/
    pause
    exit /b 1
)

:: =========================
:: CREATE VENV
:: =========================

if exist venv rmdir /s /q venv

echo Creating virtual environment...

%PYTHON_CMD% -m venv venv

if %errorlevel% neq 0 (
    echo [X] Failed to create venv.
    pause
    exit /b 1
)

echo.

:: =========================
:: INSTALL DEPENDENCIES
:: =========================

echo Installing dependencies...

call venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel -q

if not exist requirements.txt (
    echo [X] requirements.txt not found.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt

echo.
echo ==========================================
echo        Installation completed!
echo ==========================================
echo.
echo Run client : run_app.bat
echo Run server : run_server.bat
echo ==========================================
echo.

pause
