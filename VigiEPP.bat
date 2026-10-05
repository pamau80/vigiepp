@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP

REM Ya corriendo -> abrir navegador y listo
curl.exe -sf -m 3 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8000/"
  exit /b 0
)

echo.
echo  Abriendo VigiEPP...
echo.

if not exist "portable\runtime\.ready" (
  echo  Primera vez: preparando todo automaticamente.
  echo  Tarda 10-20 minutos. No cierres esta ventana.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable\setup.ps1"
  if errorlevel 1 (
    echo.
    echo  Error en la preparacion. Revisa que tengas internet.
    pause
    exit /b 1
  )
)

call "%~dp0scripts\portable\start.bat"
if errorlevel 1 (
  echo.
  echo  No arranco. Mira portable\logs\8000.log y 8001.log
  pause
  exit /b 1
)

echo  Listo.
timeout /t 2 >nul
exit /b 0
