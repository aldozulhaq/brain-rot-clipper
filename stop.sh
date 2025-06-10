#!/bin/bash
# --- Brain Rot Clipper Stopper for macOS/Linux ---

# Navigate to the script's directory
cd "$(dirname "$0")"

if [ -f server.pid ]; then
    # Read the Process ID from the file
    PID=$(cat server.pid)
    echo "Stopping server with PID: $PID..."
    
    # Kill the process
    kill $PID
    
    # Clean up the pid and log files
    rm server.pid
    rm server.log
    
    echo "Server stopped successfully."
else
    echo "Server PID file not found. It seems the server is not running."
    echo "If you are sure it is, you may need to find and stop the 'python3' process manually."
fi