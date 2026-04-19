@echo off
TITLE Aura CLI Downloader
echo Initiating Aura CLI Downloader...
echo.

:: Check if the virtual environment exists, create if not
IF NOT EXIST "venv" (
    echo [1/3] Creating a perfectly isolated Python environment to prevent global clashes...
    python -m venv venv
) ELSE (
    echo [1/3] Isolated environment found.
)

:: Activate the local isolated environment
echo [2/3] Activating environment...
call "venv\Scripts\activate.bat"

:: Install necessary packages inside the isolated folder
echo [3/3] Guaranteeing dependencies are securely installed...
pip install -q --disable-pip-version-check -r requirements.txt

echo Starting terminal interface...
echo.

:: Launch the CLI script
python downloader.py

pause
