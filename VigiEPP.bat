@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP portable

REM Si ya esta corriendo, solo abrir navegador
curl.exe -sf -m 3 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8000/"
  echo.
  echo  VigiEPP ya esta en ejecucion. Abriendo navegador...
  echo  Para cerrar todo: doble clic en DETENER.bat
  echo.
  timeout /t 4 >nul
  exit /b 0
)

echo.
echo  ========================================
echo   VigiEPP portable
echo  ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo  Primera vez: instalando dependencias...
  echo  Puede tardar 10-20 minutos. No cierres esta ventana.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable\setup.ps1"
  if errorlevel 1 (
    echo.
    pause
    exit /b 1
  )
  echo.
)

call "%~dp0scripts\portable\start.bat"
if errorlevel 1 (
  echo.
  echo  No se pudo iniciar. Revisa portable\logs\
  pause
  exit /b 1
)

echo.
echo  http://127.0.0.1:8000/   VigiEPP
echo  http://127.0.0.1:8001/   Forense
echo.
echo  Sin PIN — modo prueba
echo.
echo  Listo. El navegador deberia abrirse solo.
echo  Para cerrar: doble clic en DETENER.bat
echo.
timeout /t 8 >nul
exit /b 0
