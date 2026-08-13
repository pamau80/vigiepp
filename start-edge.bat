@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  VigiEPP — modo faena (este PC, datos locales que NO se borran)
echo  URL: http://127.0.0.1:8000  y  http://TU-IP-LAN:8000
echo.
if not exist "backend\data" mkdir "backend\data"
set VIGIEPP_DATA_DIR=%~dp0backend\data
set VIGIEPP_EPHEMERAL=0
set VIGIEPP_AUTH=1
echo  Datos en: %VIGIEPP_DATA_DIR%
echo.
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
