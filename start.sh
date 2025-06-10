#!/bin/bash
# --- Brain Rot Clipper Launcher for macOS/Linux ---

echo "==============================================="
echo "    Starting Brain Rot Clipper Server...       "
echo "==============================================="
echo

# Navigate to the script's directory so it can be run from anywhere
cd "$(dirname "$0")"

# --- Environment Setup ---
# Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "ERROR: python3 could not be found."
    echo "Please install Python 3 from python.org to continue."
    exit 1
fi

echo "[1/3] Checking for required packages..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!  ERROR: Failed to install Python packages.        !!"
    echo "!!  Check your internet connection or for errors     !!"
    echo "!!  above.                                           !!"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo
    exit 1
fi

echo
echo "[2/3] Starting server in the background..."

# Start the server using nohup to keep it running after the script exits.
# Redirect all output (stdout & stderr) to a log file.
# Run it in the background (&) and save its Process ID (PID).
nohup python3 app.py > server.log 2>&1 &
echo $! > server.pid

echo "Server started with PID: $(cat server.pid)"
echo "You can view server activity in the 'server.log' file."
echo

# Wait a few seconds for the server to initialize
sleep 3

echo "[3/3] Opening application in your default browser..."
# 'open' is the command to open files/URLs on macOS
open http://127.0.0.1:5000/

echo
echo "--------------------------------------------------------"
echo "Application is now running!"
echo "To stop the server, run the 'stop.sh' script."
echo "--------------------------------------------------------"