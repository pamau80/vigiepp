@echo off
chcp 65001 >nul
echo.
echo  Deteniendo VigiEPP y Forense...
set "KILLED=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
  set "KILLED=1"
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
  set "KILLED=1"
)
taskkill /F /FI "WINDOWTITLE eq VigiEPP-8000*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VigiEPP-8001*" >nul 2>&1
if "%KILLED%"=="1" (
  echo  Servicios detenidos.
) else (
  echo  No habia servicios en ejecucion.
)
echo.
timeout /t 3 >nul
