@echo off
TITLE Aura Web Downloader Server
echo *******************************************************
echo * Initiating Aura Web Downloader...                   *
echo *******************************************************
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
pip install -q -r requirements.txt

echo.
echo ========================================================
echo   🚀 SERVER IS LIVE!
echo   Open your browser and navigate to: http://127.0.0.1:5000
echo   To stop the server, just close this window.
echo ========================================================
echo.

:: Launch the web server
python app.py

pause
