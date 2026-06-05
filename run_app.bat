@echo off
title Stock Scanner Setup & Launcher
cls

echo ==========================================
echo   Stock Scanner - Desktop Application
echo ==========================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not added to your system PATH.
    echo.
    echo Opening Microsoft Store to install Python 3.11...
    echo Please install Python and rerun this script once the installation finishes.
    echo.
    start ms-windows-store://pdp/?ProductId=9PJPW5LDZ8C1
    pause
    exit /b
)

:: 2. Setup virtual environment if missing
if not exist ".venv" (
    echo [*] Creating virtual environment [venv] for dependencies...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [x] Error creating virtual environment.
        pause
        exit /b
    )
    echo [+] Virtual environment created successfully.
    echo.
)

:: 3. Install/Update requirements
echo [*] Checking and installing required packages...
.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [x] Error installing dependencies.
    pause
    exit /b
)
echo [+] Packages are up to date.
echo.

:: 4. Create Desktop Shortcut if not exists
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Stock Scanner.lnk"
if exist "%SHORTCUT_PATH%" goto :launch_app

echo [*] Creating a Desktop shortcut...
powershell -ExecutionPolicy Bypass -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%~dp0run_app.bat'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = 'shell32.dll,170'; $s.Save()"
if exist "%SHORTCUT_PATH%" (
    echo [+] Desktop shortcut 'Stock Scanner' created successfully!
) else (
    echo [!] Failed to create Desktop shortcut.
)
echo.

:launch_app

:: 5. Launch the app in background (no command prompt window)
echo [*] Starting Stock Scanner in background...
start "" ".venv\Scripts\pythonw.exe" desktop_app.py
echo [+] App launched! Closing launcher window...
timeout /t 3 >nul
exit
