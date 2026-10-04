@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP — iniciando

echo %CD% | findstr /I "OneDrive" >nul
if %ERRORLEVEL%==0 (
  echo  [ERROR] No ejecute desde OneDrive. Use C:\VigiEPP-prueba\
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo  Ejecute primero INSTALAR.bat
  pause
  exit /b 1
)

set ROOT=%~dp0
set PY=%ROOT%.venv\Scripts\python.exe
set VIGIEPP_DATA_DIR=%ROOT%backend\data
set VIGIEPP_FORENSE_DATA_DIR=%ROOT%forense\data
set PYTHONPATH=%ROOT%backend;%ROOT%
set VIGIEPP_AUTH=1
set VIGIEPP_EPHEMERAL=0
set VIGIEPP_COMBINED_INFERENCE=0
set VIGIEPP_ADMIN_PIN=vigiepp
set VIGIEPP_OPERATOR_PIN=porteria
set VIGIEPP_FORENSE=1
set VIGIEPP_FORENSE_LICENSE=dev
set VIGIEPP_ALLOW_DEFAULT_PINS=1
set VIGIEPP_COOKIE_SECURE=0

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set %%a=%%b
  )
)

echo.
echo  VigiEPP  -> http://127.0.0.1:8000/
echo  Forense  -> http://127.0.0.1:8001/
echo  PIN admin: vigiepp  |  porteria: porteria
echo.

start "VigiEPP-8000" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_AUTH=1 && set VIGIEPP_ADMIN_PIN=%VIGIEPP_ADMIN_PIN% && set VIGIEPP_OPERATOR_PIN=%VIGIEPP_OPERATOR_PIN% && set VIGIEPP_EPHEMERAL=0 && set VIGIEPP_COMBINED_INFERENCE=0 && set VIGIEPP_ALLOW_DEFAULT_PINS=1 && %PY% -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend"

timeout /t 4 /nobreak >nul

start "Forense-8001" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend;%ROOT% && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_FORENSE_DATA_DIR=%VIGIEPP_FORENSE_DATA_DIR% && set VIGIEPP_AUTH=1 && set VIGIEPP_ADMIN_PIN=%VIGIEPP_ADMIN_PIN% && set VIGIEPP_FORENSE=1 && set VIGIEPP_FORENSE_LICENSE=dev && %PY% -m uvicorn forense.app.main:app --host 0.0.0.0 --port 8001"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000/"
start "" "http://127.0.0.1:8001/"

echo  Servicios iniciados. Use DETENER.bat para cerrar.
echo.
pause
