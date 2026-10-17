@echo off
cd /d "%~dp0"
start "Kavach API :8000" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --no-proxy-headers --host 127.0.0.1 --port 8000"
start "Kavach UI :3000" cmd /k "cd /d %~dp0frontend && npm run dev"
start "College Portal :3001" cmd /k "cd /d %~dp0portals\college-portal && npm run dev"
start "Citizen Portal :5000" cmd /k "cd /d %~dp0portals\citizen-portal && call .venv\Scripts\activate.bat && flask --app app run -h 127.0.0.1 -p 5000"
start "Attack Lab :4000" /d "%~dp0attack-lab" cmd /k "..\backend\.venv\Scripts\python.exe -m uvicorn lab:app --host 127.0.0.1 --port 4000"
echo Starting... open http://localhost:3000 in a few seconds.
echo Attack Lab: http://localhost:3000/lab  (or the standalone page http://127.0.0.1:4000)
ping -n 5 127.0.0.1 >nul
start "" http://localhost:3000
