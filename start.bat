@echo off
echo Starting Voice Assistant...

REM Start Backend Server in a new window
echo Starting Backend Server...
start "Voice Assistant Backend" cmd /c "python run_server.py"

REM Wait for 3 seconds to ensure backend is fully started
timeout /t 3 /nobreak >nul

REM Start Frontend UI
echo Starting Frontend UI...
cd frontend
npm start
