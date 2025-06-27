#!/bin/bash

cd /Users/jessica.steed/Documents/GitHub/mov-processor-web || exit 1

# Create venv if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate || exit 1

# Install requirements if needed
pip install -r requirements.txt

# Launch the Flask app in background
python3 app.py &

# Wait for the server to start
sleep 3

# Open browser
open http://127.0.0.1:5050/

# Keep terminal open if app crashes
wait