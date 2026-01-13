# MedData Platform - Enterprise V5.0

## Overview
This is the backend system for the MedData Platform, built with Python (FastAPI) and SQLite. It manages employees, projects, audit tasks, and payments.

## Prerequisites
- **Python 3.9+** installed and added to `PATH`.

## Quick Start (Recommended)
1. Double-click the `run.bat` file in this directory.
2. The script will automatically:
   - Install required dependencies.
   - Initialize the database (`medical_platform.db`).
   - Start the web server.
3. Open your browser and go to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Fast Restart (For Testing)
If you are restarting the server frequently, use **`dev.bat`**.
- It skips dependency checks.
- It skips database checks.
- It just starts the server instantly.

## Manual Setup
If you prefer to run commands manually:

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**
   ```bash
   python setup_database.py
   ```

3. **Start Server**
   ```bash
   uvicorn main:app --reload
   ```

## Default Credentials
The database setup script creates these default users:

| Role | Username | Password |
|------|----------|----------|
| **Master Admin** | `Admin` | `admin123` |
| **Admin** | `Rohit` | `admin01` |
| **Employee** | `Vipin` | `vipin01` |

## Project Structure
- `main.py`: Entry point for the FastAPI application.
- `setup_database.py`: Script to create tables and seed initial data.
- `requirements.txt`: Python dependencies.
- `medical_platform.db`: SQLite database file (created after setup).
- `static/` & `templates/`: Frontend assets and HTML files.
