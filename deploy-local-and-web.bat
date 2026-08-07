@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  ========================================
echo   VigiEPP — deploy LOCAL + WEB (Railway)
echo  ========================================
echo.

REM --- LOCAL ---
echo [1/2] Local (puerto 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
  taskkill /F /PID %%a >nul 2>&1
)
set VIGIEPP_ADMIN_PIN=VigiEPP-sadgYGr0
set VIGIEPP_OPERATOR_PIN=porteria
set VIGIEPP_AUTH=1
set VIGIEPP_COOKIE_SECURE=0
start "VigiEPP-local" /MIN backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend
timeout /t 3 /nobreak >nul
curl.exe -sS -m 8 http://127.0.0.1:8000/api/health
echo.
echo   Local:  http://127.0.0.1:8000/
echo   Celular (misma WiFi): http://TU_IP_LAN:8000/
echo.

REM --- WEB (Railway) ---
echo [2/2] Web Railway (requiere RAILWAY_TOKEN en el entorno)...
if "%RAILWAY_TOKEN%"=="" (
  echo   [!] Definí RAILWAY_TOKEN y volvé a correr, o pedile al agente el deploy web.
  echo   Web actual: https://vigiepp-production.up.railway.app/
  goto end
)

set PROJECT=aa325e64-d928-46c2-933a-d04de62e3341
set ENVID=2c0f46c4-f2c9-4603-b232-9f5cbd78dfbe
set SERVICE=b900cb86-2edf-4efe-a4bf-aa450d31a453
set TAR=%TEMP%\vigiepp-deploy-light.tar.gz
if exist "%TAR%" del /f "%TAR%"
tar.exe -czf "%TAR%" --exclude=.venv --exclude=backend/.venv --exclude=__pycache__ --exclude=backend/runs --exclude=backend/datasets --exclude=.git --exclude=backend/models --exclude=backend/yolov8n.pt --exclude=backend/data/models --exclude=backend/data/faces --exclude=backend/data/evidence --exclude=agent-tools --exclude=hardware --exclude=_audit_prod Dockerfile railway.toml render.yaml backend frontend
curl.exe -sS -k -m 600 -X POST "https://backboard.railway.com/project/%PROJECT%/environment/%ENVID%/up?serviceId=%SERVICE%&message=dual-deploy" -H "Authorization: Bearer %RAILWAY_TOKEN%" -H "Content-Type: multipart/form-data" -F "file=@%TAR%"
echo.
echo   Web: https://vigiepp-production.up.railway.app/

:end
echo.
echo Listo.
pause
