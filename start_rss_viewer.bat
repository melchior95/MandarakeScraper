@echo off
cd /d "%~dp0"
echo Starting Mandarake RSS Viewer...
echo.
echo Server will start at http://localhost:5000
echo Press Ctrl+C to stop
echo.
venv\Scripts\python.exe "archive\yahoo_auction\rss_web_viewer.py"
pause
