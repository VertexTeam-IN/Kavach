@echo off
setlocal
echo === Kavach setup ===

rem Pick a normal (not free-threaded) Python 3.12 or 3.11 for the virtual environments
set PY=
py -3.12 -c "import sys; assert not hasattr(sys, '_is_gil_enabled') or sys._is_gil_enabled()" >nul 2>&1 && set PY=py -3.12
if not defined PY py -3.11 -c "import sys" >nul 2>&1 && set PY=py -3.11
if not defined PY set PY=python
echo Using: %PY%
%PY% --version

echo.
echo [1/4] Backend (Python)
cd /d "%~dp0backend" || goto :error
if not exist .venv %PY% -m venv .venv || goto :error
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :error
if not exist .env copy .env.example .env
call deactivate

echo.
echo [2/4] Kavach UI (Node)
cd /d "%~dp0frontend" || goto :error
call npm install || goto :error

echo.
echo [3/4] College portal (Node)
cd /d "%~dp0portals\college-portal" || goto :error
call npm install || goto :error

echo.
echo [4/4] Citizen portal (Python)
cd /d "%~dp0portals\citizen-portal" || goto :error
if not exist .venv %PY% -m venv .venv || goto :error
call .venv\Scripts\activate.bat || goto :error
pip install -r requirements.txt || goto :error
call deactivate

echo.
echo === Setup complete. Now run start-all.bat ===
pause
exit /b 0

:error
echo.
echo *** Setup failed. Scroll up for the error message. ***
pause
exit /b 1
