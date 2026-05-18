@echo off
cd /d "%~dp0"

echo ========================================
echo  FeedbackRadar Agentic
echo ========================================

echo [1/3] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [2/3] Arrancando FastAPI en puerto 8000...
start "FeedbackRadar - Backend" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo     Esperando a que el backend este listo...
timeout /t 5 /nobreak >nul

echo [3/3] Arrancando Streamlit en puerto 8501...
venv\Scripts\streamlit.exe run frontend\streamlit_app.py --server.port 8501

pause
