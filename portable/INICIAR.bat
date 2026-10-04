@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP portable

set ROOT=%~dp0
set PY=%ROOT%python\python.exe

if not exist "%PY%" (
  echo  [ERROR] Falta Python embebido en %ROOT%python\
  echo  Use el paquete "zero-admin" generado con build_portable_pc.sh
  pause
  exit /b 1
)

set VIGIEPP_DATA_DIR=%ROOT%backend\data
set VIGIEPP_FORENSE_DATA_DIR=%ROOT%forense\data
set PYTHONPATH=%ROOT%backend;%ROOT%
set VIGIEPP_AUTH=0
set VIGIEPP_EPHEMERAL=0
set VIGIEPP_COMBINED_INFERENCE=0
set VIGIEPP_FORENSE=1
set VIGIEPP_FORENSE_LICENSE=dev
set VIGIEPP_COOKIE_SECURE=0
set VIGIEPP_ALLOW_DEFAULT_PINS=1

if exist "%ROOT%env.portable.example" if not exist "%ROOT%.env" copy /Y "%ROOT%env.portable.example" "%ROOT%.env" >nul
if exist "%ROOT%.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%ROOT%.env") do (
    if not "%%a"=="" set "%%a=%%b"
  )
)

echo.
echo  VigiEPP portable — sin permisos de administrador
echo  VigiEPP:  http://127.0.0.1:8000/
echo  Forense:  http://127.0.0.1:8001/
if "%VIGIEPP_AUTH%"=="0" (echo  Acceso: sin PIN ^(modo prueba^)) else (echo  PIN admin: vigiepp)
echo.

start "VigiEPP-8000" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_AUTH=%VIGIEPP_AUTH% && set VIGIEPP_EPHEMERAL=0 && set VIGIEPP_COMBINED_INFERENCE=0 && set VIGIEPP_ALLOW_DEFAULT_PINS=1 && "%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend"

timeout /t 5 /nobreak >nul

start "Forense-8001" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend;%ROOT% && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_FORENSE_DATA_DIR=%VIGIEPP_FORENSE_DATA_DIR% && set VIGIEPP_AUTH=%VIGIEPP_AUTH% && set VIGIEPP_FORENSE=1 && set VIGIEPP_FORENSE_LICENSE=dev && "%PY%" -m uvicorn forense.app.main:app --host 127.0.0.1 --port 8001"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8000/"
start "" "http://127.0.0.1:8001/"

echo  Listo. Para cerrar: DETENER.bat
echo.
pause
