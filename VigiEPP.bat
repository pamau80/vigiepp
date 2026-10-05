@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP

REM Todo local: esta carpeta (USB, Escritorio, Documentos). Sin admin.
set "VIGIEPP_DATA_DIR=%~dp0backend\data"
set "VIGIEPP_FORENSE_DATA_DIR=%~dp0forense\data"

curl.exe -sf -m 3 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8000/"
  exit /b 0
)

if not exist "portable\runtime\python\python.exe" (
  echo.
  echo  Falta el paquete COMPLETO pre-armado.
  echo.
  echo  Para PCs sin permisos de administrador use:
  echo    vigiepp-portable-full.zip
  echo.
  echo  Descargalo desde GitHub:
  echo    Actions -^> Build portable Windows -^> ultimo run -^> Artifacts
  echo.
  echo  Solo descomprima el ZIP en USB o Escritorio y vuelva a abrir VigiEPP.bat
  echo  No instala nada en Windows.
  echo.
  pause
  exit /b 1
)

echo.
echo  Abriendo VigiEPP...
call "%~dp0scripts\portable\start.bat"
if errorlevel 1 (
  echo.
  echo  Error al iniciar. Ver portable\logs\
  pause
  exit /b 1
)
exit /b 0
