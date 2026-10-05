@echo off
setlocal
chcp 65001 >nul
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

set "PY=%ROOT%\portable\runtime\python\python.exe"
if not exist "%PY%" set "PY=%ROOT%\.venv\Scripts\python.exe"
set "LOG_DIR=%ROOT%\portable\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%PY%" exit /b 1

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

if not exist "%ROOT%\backend\data" mkdir "%ROOT%\backend\data"
if not exist "%ROOT%\forense\data" mkdir "%ROOT%\forense\data"

start "VigiEPP-8000" /MIN "%ROOT%\portable\run\start-8000.cmd"
call "%~dp0wait_health.bat" "http://127.0.0.1:8000/api/health" "VigiEPP" 60
if errorlevel 1 exit /b 1

start "VigiEPP-8001" /MIN "%ROOT%\portable\run\start-8001.cmd"
call "%~dp0wait_health.bat" "http://127.0.0.1:8001/api/forense/health" "Forense" 60
if errorlevel 1 exit /b 1

start "" "http://127.0.0.1:8000/"
exit /b 0
