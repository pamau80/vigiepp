@echo off
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VigiEPP-8000*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VigiEPP-8001*" >nul 2>&1
