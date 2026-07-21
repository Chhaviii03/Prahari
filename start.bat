@echo off
echo Starting PRAHARI Backend...
cd backend
start "PRAHARI API" cmd /k "python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
echo Starting PRAHARI Frontend...
cd ..\frontend
start "PRAHARI UI" cmd /k "npm run dev"
echo.
echo PRAHARI is starting...
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo   Login: safety / prahari
