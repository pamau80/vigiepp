@echo off
cd /d "%~dp0"

REM Si abrieron el bat dentro de subcarpeta portable\, subir un nivel
if not exist "python\python.exe" if exist "..\python\python.exe" cd /d "%~dp0.."

set "ROOT=%CD%\"
set "PY=%ROOT%python\python.exe"

if not exist "%PY%" (
  echo.
  echo  ERROR: No esta python\python.exe
  echo  Descomprimio el ZIP completo en C:\VigiEPP-prueba\ ?
  echo  Debe ver la carpeta python\ junto a INICIAR.bat
  echo.
  pause
  exit /b 1
)

set "VIGIEPP_DATA_DIR=%ROOT%backend\data"
set "VIGIEPP_FORENSE_DATA_DIR=%ROOT%forense\data"
set "PYTHONPATH=%ROOT%backend;%ROOT%"
set "VIGIEPP_AUTH=0"
set "VIGIEPP_EPHEMERAL=0"
set "VIGIEPP_COMBINED_INFERENCE=0"
set "VIGIEPP_FORENSE=1"
set "VIGIEPP_FORENSE_LICENSE=dev"
set "VIGIEPP_COOKIE_SECURE=0"
set "VIGIEPP_ALLOW_DEFAULT_PINS=1"

echo.
echo  VigiEPP portable
echo  http://127.0.0.1:8000/  y  http://127.0.0.1:8001/
echo  Sin PIN - modo prueba
echo.

start "VigiEPP-8000" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_AUTH=0 && set VIGIEPP_EPHEMERAL=0 && set VIGIEPP_COMBINED_INFERENCE=0 && set VIGIEPP_ALLOW_DEFAULT_PINS=1 && \"%PY%\" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend"

timeout /t 5 /nobreak >nul

start "Forense-8001" /MIN cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%backend;%ROOT% && set VIGIEPP_DATA_DIR=%VIGIEPP_DATA_DIR% && set VIGIEPP_FORENSE_DATA_DIR=%VIGIEPP_FORENSE_DATA_DIR% && set VIGIEPP_AUTH=0 && set VIGIEPP_FORENSE=1 && set VIGIEPP_FORENSE_LICENSE=dev && \"%PY%\" -m uvicorn forense.app.main:app --host 127.0.0.1 --port 8001"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8000/"
start "" "http://127.0.0.1:8001/"

echo  Listo. Cerrar con DETENER.bat
pause
