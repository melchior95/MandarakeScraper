@echo off
cd /d "%~dp0"
echo Starting Mandarake RSS Viewer...
echo Opening Chrome in 3 seconds...
echo.

REM Start server in background
start /min "Mandarake RSS Server" venv\Scripts\python.exe "archive\yahoo_auction\rss_web_viewer.py"

REM Wait 3 seconds for server to start
timeout /t 3 /nobreak > nul

REM Try to open Chrome (multiple common installation paths)
set CHROME_FOUND=0

REM Standard Chrome installation path
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:5000
    set CHROME_FOUND=1
)

REM Chrome in Program Files (x86)
if %CHROME_FOUND%==0 (
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" http://localhost:5000
        set CHROME_FOUND=1
    )
)

REM Chrome in user AppData
if %CHROME_FOUND%==0 (
    if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
        start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" http://localhost:5000
        set CHROME_FOUND=1
    )
)

REM If Chrome not found, fall back to default browser
if %CHROME_FOUND%==0 (
    echo Chrome not found, opening with default browser...
    start http://localhost:5000
)

echo.
echo RSS Viewer is now running in Chrome!
echo Close this window to stop the server.
echo.
pause
