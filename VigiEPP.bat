@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP

set "VIGIEPP_DATA_DIR=%~dp0backend\data"
set "VIGIEPP_FORENSE_DATA_DIR=%~dp0forense\data"

curl.exe -sf -m 3 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8000/"
  exit /b 0
)

if not exist "portable\runtime\python\python.exe" (
  echo.
  echo  Paquete incompleto. Descargue VigiEPP.zip desde GitHub Releases.
  echo.
  pause
  exit /b 1
)

echo.
echo  Abriendo VigiEPP...
start "VigiEPP" /MIN "%~dp0portable\run\launch.cmd"

set /a N=0
:wait_loop
curl.exe -sf -m 3 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel%==0 goto open_browser
timeout /t 2 /nobreak >nul
set /a N+=1
if %N% lss 45 goto wait_loop

echo.
echo  No arranco. Revise portable\logs\8000.log y 8001.log
pause
exit /b 1

:open_browser
start "" "http://127.0.0.1:8000/"
exit /b 0
