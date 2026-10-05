@echo off
setlocal EnableDelayedExpansion
REM Uso: wait_health.bat URL ETIQUETA [intentos]
set "URL=%~1"
set "LABEL=%~2"
set "MAX=%~3"
if "%MAX%"=="" set "MAX=45"
set /a N=0
:loop
curl.exe -sf -m 3 "%URL%" >nul 2>&1
if !errorlevel!==0 (
  echo   OK %LABEL%
  exit /b 0
)
timeout /t 2 /nobreak >nul
set /a N+=1
if !N! lss %MAX% goto loop
echo   ERROR: %LABEL% no respondio en %URL%
exit /b 1
