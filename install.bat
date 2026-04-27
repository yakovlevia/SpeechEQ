@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==========================================
echo        SpeechEQ Installer
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Current directory: %cd%
echo.

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

        echo Winget not available.
        echo Please download FFmpeg manually:
        echo https://www.gyan.dev/ffmpeg/builds/

    ) else (

        echo Installing FFmpeg...
        winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements

        if !errorlevel! neq 0 (
            echo [!] FFmpeg installation failed.
        ) else (
            echo [+] FFmpeg installed. Restart terminal if PATH not updated.
        )

    )

) else (

    echo [+] FFmpeg already installed.

)

echo.

:: =========================
:: PYTHON CHECK
:: =========================

:: =========================
:: PYTHON CHECK / INSTALL
:: =========================

echo Checking Python...

where python >nul 2>&1

if %errorlevel% neq 0 (

    echo Python not found.

    where winget >nul 2>&1
    if %errorlevel% neq 0 (

        echo [X] Winget not available.
        echo Please install Python manually:
        echo https://www.python.org/downloads/
        pause
        exit /b 1

    ) else (

        echo Installing Python...

        winget install --id Python.Python.3 -e --accept-package-agreements --accept-source-agreements

        if %errorlevel% neq 0 (
            echo [X] Python installation failed.
            pause
            exit /b 1
        )

        echo Python installed. Reloading PATH...

        set "PATH=%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\Scripts\"

    )

)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i

echo Python version: %PYTHON_VERSION%
echo.

:: =========================
:: CREATE VENV
:: =========================

if exist venv rmdir /s /q venv

echo Creating virtual environment...

python -m venv venv

if %errorlevel% neq 0 (
    echo [X] Failed to create venv
    pause
    exit /b 1
)

echo.

:: =========================
:: INSTALL DEPENDENCIES
:: =========================

echo Installing dependencies...

call venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel

if not exist requirements.txt (
    echo [X] requirements.txt not found.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt

echo.
echo ==========================================
echo        Installation completed
echo ==========================================
echo.
echo Run client : run_app.bat
echo Run server : run_server.bat
echo ==========================================
echo.

pause