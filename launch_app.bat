@echo off
cd /d %~dp0

:: Activate virtual environment
call venv\Scripts\activate

:: Launch browser
start "" "http://127.0.0.1:5000/"

:: Run Flask app
python app.py