@echo off
echo Cerrando VigiEPP y Forense...
taskkill /FI "WINDOWTITLE eq VigiEPP-8000*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Forense-8001*" /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
echo Listo.
timeout /t 2 /nobreak >nul
