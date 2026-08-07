@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  VigiEPP → Render
echo  1) Abre https://dashboard.render.com/u/settings#api-keys
echo  2) Crea API Key y pegala abajo
echo  3) Necesitas el repo en GitHub (Render construye desde Git)
echo.
set /p RENDER_API_KEY="RENDER_API_KEY: "
if "%RENDER_API_KEY%"=="" (
  echo Falta API key.
  pause
  exit /b 1
)
curl.exe -sS -m 20 -H "Authorization: Bearer %RENDER_API_KEY%" -H "Accept: application/json" "https://api.render.com/v1/owners?limit=5"
echo.
echo.
echo Si viste tu owner OK, sigue en el Dashboard:
echo   New + → Blueprint → conecta este repo (con render.yaml)
echo   PIN admin cuando pregunte: el de .admin-pin.local.txt
echo.
pause
