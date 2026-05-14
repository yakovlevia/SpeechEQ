@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ==========================================
echo        SpeechEQ Installer
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "REQUIRED_MAJOR=3"
set "REQUIRED_MINOR=10"

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

echo Checking Python %REQUIRED_MAJOR%.%REQUIRED_MINOR%.x...

set "PYTHON_CMD="

:: Ищем Python 3.10.x
for /f "tokens=*" %%p in ('where python 2^>nul') do (
    for /f "tokens=2" %%v in ('"%%p" --version 2^>^&1') do (
        for /f "tokens=1,2 delims=." %%a in ("%%v") do (
            if "%%a"=="%REQUIRED_MAJOR%" if "%%b"=="%REQUIRED_MINOR%" (
                if not defined PYTHON_CMD set "PYTHON_CMD=%%p"
            )
        )
    )
)

:: Также проверим py launcher
if not defined PYTHON_CMD (
    py -3.10 --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=py -3.10"
)

if not defined PYTHON_CMD (
    echo Python %REQUIRED_MAJOR%.%REQUIRED_MINOR%.x not found. Installing via winget...
    echo.

    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo [X] Winget not available.
        echo     Download Python %REQUIRED_MAJOR%.%REQUIRED_MINOR% manually: https://www.python.org/downloads/release/python-31012/
        pause
        exit /b 1
    )

    winget install --id Python.Python.3.10 -e --accept-package-agreements --accept-source-agreements

    if !errorlevel! neq 0 (
        echo [X] Python %REQUIRED_MAJOR%.%REQUIRED_MINOR% installation failed.
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

:: Проверяем версию 3.10.x
for /f "tokens=2" %%i in ('"%PYTHON_CMD%" --version 2^>^&1') do set PY_VER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if not "%PY_MAJOR%"=="%REQUIRED_MAJOR%" (
    echo [X] Python %REQUIRED_MAJOR%.%REQUIRED_MINOR%.x required, found %PY_VER%.
    pause
    exit /b 1
)
if not "%PY_MINOR%"=="%REQUIRED_MINOR%" (
    echo [X] Python %REQUIRED_MAJOR%.%REQUIRED_MINOR%.x required, found %PY_VER%.
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

python -m pip install --upgrade pip setuptools -q

if not exist requirements.txt (
    echo [X] requirements.txt not found.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt

:: k2 (ASR-интеграция speechbrain) недоступен через pip — ставим заглушку
python -c "import k2" 2>nul || python -c ^
"import sys, os; site=[p for p in sys.path if 'site-packages' in p][0]; d=os.path.join(site,'k2'); os.makedirs(d,exist_ok=True); open(os.path.join(d,'__init__.py'),'w').close(); print('[+] k2 stub installed')"

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
