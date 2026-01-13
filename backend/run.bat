@echo off
SETLOCAL
TITLE MedData Platform - Startup Script

echo ========================================================
echo       MedData Platform - Enterprise V5.0 Setup
echo ========================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.9+ from python.org and try again.
    pause
    exit /b
)
echo [OK] Python is found.

:: 2. Install Dependencies
echo.
echo [STEP 1/3] Installing Dependencies...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

:: 3. Setup Database
echo.
echo [STEP 2/3] Setting up Database...
python setup_database.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Database setup failed.
    pause
    exit /b
)

:: 4. Start Server
echo.
echo [STEP 3/3] Starting Server...
echo.
echo Access the application at: http://127.0.0.1:8000
echo Admin Dashboard: http://127.0.0.1:8000/admin-dashboard
echo.
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

ENDLOCAL
