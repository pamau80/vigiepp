@echo off
REM Devuelve la ruta al python portable (exit 1 si no existe)
set "ROOT=%~dp0..\.."
if exist "%ROOT%\portable\runtime\python\python.exe" (
  set "VIGIEPP_PY=%ROOT%\portable\runtime\python\python.exe"
  exit /b 0
)
if exist "%ROOT%\.venv\Scripts\python.exe" (
  set "VIGIEPP_PY=%ROOT%\.venv\Scripts\python.exe"
  exit /b 0
)
exit /b 1
