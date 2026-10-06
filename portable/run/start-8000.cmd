@echo off
cd /d "%~dp0..\.."
set "PY=%CD%\portable\runtime\python\python.exe"
if not exist "%PY%" set "PY=%CD%\.venv\Scripts\python.exe"
set "PYTHONPATH=%CD%\backend"
set "VIGIEPP_DATA_DIR=%CD%\backend\data"
set "VIGIEPP_AUTH=0"
set "VIGIEPP_EPHEMERAL=0"
set "VIGIEPP_COMBINED_INFERENCE=0"
set "VIGIEPP_DOCS=1"
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend >> "%CD%\portable\logs\8000.log" 2>&1
