@echo off
echo Starting Voice Assistant...

REM Check TTS mode
echo Checking TTS configuration...
python -c "import sys, yaml; config=yaml.safe_load(open('config/settings.yaml', encoding='utf-8')); sys.exit(0 if config.get('tts', {}).get('mode') == 'local' else 1)"
if %ERRORLEVEL% EQU 0 (
    REM Start GPT-SoVITS TTS Server (Local TTS Backend)
    echo Starting GPT-SoVITS TTS Server...
    cd /d "%~dp0tools\GPT-SoVITS-Inference"
    start "GPT-SoVITS TTS Server" cmd /c "runtime\python.exe Inference\src\tts_backend.py"
    cd /d "%~dp0"

    REM Wait for 5 seconds to ensure TTS server is ready
    timeout /t 5 /nobreak >nul
) else (
    echo TTS mode is not local. Skipping GPT-SoVITS local server...
)

REM Start Backend Server in a new window
echo Starting Backend Server...
start "Voice Assistant Backend" cmd /c "python run_server.py"

REM Wait for 3 seconds to ensure backend is fully started
timeout /t 3 /nobreak >nul

REM Start Frontend UI
echo Starting Frontend UI...
cd frontend
npm start
