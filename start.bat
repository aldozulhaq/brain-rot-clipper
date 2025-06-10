@echo off
REM --- Brain Rot Clipper Launcher (Final, Direct Interpreter Method) ---

TITLE Brain Rot Clipper Server

ECHO =============================================================
ECHO ==                                                         ==
ECHO ==           BRAIN ROT CLIPPER - SERVER LAUNCHER           ==
ECHO ==                                                         ==
ECHO =============================================================
ECHO.
ECHO This window will now configure the environment and run the server.
ECHO Please keep this window open to use the application.
ECHO.
ECHO To STOP the server, simply close this window.
ECHO.
ECHO -------------------------------------------------------------
ECHO.

:: Change directory to the script's location
cd /d "%~dp0"

:: Step 1 & 2: Ensure pip and install packages using the 'py' launcher
:: (Using 'py' for setup is still best practice as it's more flexible)
ECHO [1/4] Checking Python package manager (pip)...
py -m ensurepip --upgrade > nul 2>&1

ECHO [2/4] Installing required packages...
py -m pip install -r requirements.txt
IF %errorlevel% NEQ 0 (
    ECHO.
    ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ECHO !!  ERROR: Could not install packages.                      !!
    ECHO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ECHO.
    PAUSE
    EXIT /B
)

ECHO.
ECHO [3/4] Launching the application in your web browser...
timeout /t 3 /nobreak > nul
start "" "http://127.0.0.1:5000/"

:: Step 4: Run the application server using the direct interpreter
ECHO [4/4] Starting the server. The application is now running.
ECHO -------------------------------------------------------------
ECHO.
python app.py

:: The batch script will wait here until the python.exe process is closed.