@echo off
cd /d "%~dp0..\.."
set "PYTHONPATH=%CD%\backend;%CD%"
set "VIGIEPP_FORENSE=1"
set "VIGIEPP_FORENSE_LICENSE=dev"
set "VIGIEPP_FORENSE_DATA_DIR=%CD%\forense\data"
set "VIGIEPP_AUTH=0"
set "VIGIEPP_COMBINED_INFERENCE=0"
"%CD%\.venv\Scripts\python.exe" -m uvicorn forense.app.main:app --host 0.0.0.0 --port 8001 >> "%CD%\portable\logs\8001.log" 2>&1
