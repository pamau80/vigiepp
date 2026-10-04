@echo off
chcp 65001 >nul
echo Deteniendo VigiEPP (8000) y Forense (8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
echo Listo.
timeout /t 2 /nobreak >nul
