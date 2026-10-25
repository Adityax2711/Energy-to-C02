@echo off
title Energy-to-CO2 Translation Engine (24/7 Live Server)
color 0b

echo ===============================================================================
echo        ENERGY-TO-CO2 TRANSLATION ENGINE - 24/7 LIVE SERVER RUNNER
echo ===============================================================================
echo.
echo Local Dashboard:      http://localhost:8000
echo OpenAPI Docs:         http://localhost:8000/docs
echo Prometheus Metrics:   http://localhost:8000/metrics
echo System Health:        http://localhost:8000/health
echo.
echo Host Binding:         0.0.0.0:8000 (accessible on LAN & localhost)
echo Auto-Recovery:        Active (automatically restarts if terminated)
echo ===============================================================================
echo.

cd /d "%~dp0"

:loop
echo [%date% %time%] Starting Energy-to-CO2 Engine...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo [ERROR] Virtual environment .venv not found. Running with global python...
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)

echo.
echo [WARNING] Server stopped at %time% (Exit code: %errorlevel%).
echo [RELOAD] Restarting 24/7 live server in 3 seconds... (Press Ctrl+C to stop)
timeout /t 3 /nobreak >nul
goto loop
