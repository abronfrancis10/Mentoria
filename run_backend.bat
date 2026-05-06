@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   Mentoria - Starting Backend Server
echo ==========================================

REM Navigate to the backend directory relative to this script
cd /d "%~dp0backend"

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found in backend directory.
    echo Please create it based on your configuration.
)

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Creating virtual environment...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created successfully.
    
    echo [INFO] Installing dependencies...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Found existing virtual environment.
    call venv\Scripts\activate.bat
)

echo [INFO] Ensuring Ollama model is available...
ollama pull llama3.2:1b

echo [INFO] Starting FastAPI server on http://localhost:8000
echo [INFO] Press Ctrl+C to stop the server.
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend server stopped unexpectedly with error code %errorlevel%.
    pause
)

pause
