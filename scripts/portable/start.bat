@echo off
setlocal
chcp 65001 >nul
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

set "PY=%ROOT%\.venv\Scripts\python.exe"
set "LOG_DIR=%ROOT%\portable\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%PY%" (
  echo.
  echo  ERROR: Entorno no instalado. Ejecuta VigiEPP.bat de nuevo.
  exit /b 1
)

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

if not exist "%ROOT%\backend\data" mkdir "%ROOT%\backend\data"
if not exist "%ROOT%\forense\data" mkdir "%ROOT%\forense\data"

echo.
echo  Iniciando VigiEPP en :8000...
start "VigiEPP-8000" /MIN "%ROOT%\portable\run\start-8000.cmd"
call "%~dp0wait_health.bat" "http://127.0.0.1:8000/api/health" "VigiEPP"
if errorlevel 1 (
  echo  Revisa el log: portable\logs\8000.log
  exit /b 1
)

echo  Iniciando Forense en :8001...
start "VigiEPP-8001" /MIN "%ROOT%\portable\run\start-8001.cmd"
call "%~dp0wait_health.bat" "http://127.0.0.1:8001/api/forense/health" "Forense"
if errorlevel 1 (
  echo  Revisa el log: portable\logs\8001.log
  exit /b 1
)

start "" "http://127.0.0.1:8000/"
exit /b 0
