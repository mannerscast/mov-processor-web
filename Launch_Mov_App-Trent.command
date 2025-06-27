#!/bin/bash

# Navigate to project directory
cd /Users/trent.armstrong/Documents/GitHub/mov-processor-web || exit 1

# Kill any previous app.py processes
pkill -f "python.*app.py"

# Activate virtual environment
source .venv/bin/activate || exit 1

# Detect local IP (try en0 first, fallback to en1)
LOCAL_IP=$(ipconfig getifaddr en0)
if [ -z "$LOCAL_IP" ]; then
  LOCAL_IP=$(ipconfig getifaddr en1)
fi

if [ -z "$LOCAL_IP" ]; then
  echo "❌ Could not determine local IP address. Is Wi-Fi or Ethernet enabled?"
  exit 1
fi

# Show access URL for phone/tablet use
echo "🌐 Access the app from your phone at: http://$LOCAL_IP:5050/"

# Open the app in the default browser
open "http://$LOCAL_IP:5050/"

# Launch the Flask app (in foreground so terminal stays open)
exec python3 app.py