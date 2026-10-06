@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0portable\run\stop.cmd"
echo VigiEPP cerrado.
timeout /t 2 >nul
