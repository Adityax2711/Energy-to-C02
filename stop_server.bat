@echo off
title Stop Energy-to-CO2 Server
color 0c

echo Stopping any running server process on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    if not "%%a"=="" (
        echo Killing process PID %%a...
        taskkill /f /pid %%a >nul 2>&1
    )
)
echo Done! Port 8000 is now free.
pause
