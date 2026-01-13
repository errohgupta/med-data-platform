@echo off
TITLE MedData Platform - Fast Dev Server

echo ========================================================
echo       MedData Platform - Fast Dev Mode
echo ========================================================
echo.
echo [INFO] Skipping dependency and database checks.
echo.
echo Access the application at: http://127.0.0.1:8000
echo.

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
