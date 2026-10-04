@echo off
chcp 65001 >nul
cd /d "%~dp0"
title VigiEPP — instalación portable

echo.
echo  ========================================
echo   VigiEPP portable — INSTALACION
echo   (extraccion FUERA de OneDrive)
echo  ========================================
echo.

echo %CD% | findstr /I "OneDrive" >nul
if %ERRORLEVEL%==0 (
  echo  [ERROR] Esta carpeta esta dentro de OneDrive.
  echo  Mueva el paquete a C:\VigiEPP-prueba\ e intente de nuevo.
  echo.
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Python no encontrado. Instale Python 3.12 desde python.org
  echo          y marque "Add python.exe to PATH".
  pause
  exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Python: %PYVER%

if not exist ".venv\Scripts\python.exe" (
  echo  [1/4] Creando entorno virtual...
  python -m venv .venv
  if errorlevel 1 (
    echo  [ERROR] No se pudo crear .venv
    pause
    exit /b 1
  )
) else (
  echo  [1/4] Entorno virtual ya existe.
)

set PY=%~dp0.venv\Scripts\python.exe
set PIP=%~dp0.venv\Scripts\pip.exe

echo  [2/4] Instalando PyTorch CPU...
"%PIP%" install --upgrade pip -q
"%PIP%" install torch torchvision --index-url https://download.pytorch.org/whl/cpu -q

echo  [3/4] Instalando dependencias VigiEPP + Forense...
"%PIP%" install -r backend\requirements.txt -q
"%PIP%" install -r forense\requirements.txt -q

if not exist "backend\data" mkdir "backend\data"
if not exist "backend\data\models" mkdir "backend\data\models"
if not exist "backend\data\faces" mkdir "backend\data\faces"
if not exist "backend\models" mkdir "backend\models"
if not exist "forense\data" mkdir "forense\data"

echo  [4/4] Verificando modelos IA...
if not exist "backend\models\best_ppe.pt" (
  echo         Descargando modelo EPP...
  curl.exe -fsSL -o "backend\models\best_ppe.pt" "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt"
)
if not exist "backend\data\models\face_detection_yunet_2023mar.onnx" (
  echo         Descargando YuNet...
  curl.exe -fsSL -o "backend\data\models\face_detection_yunet_2023mar.onnx" "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
if not exist "backend\data\models\face_recognition_sface_2021dec.onnx" (
  echo         Descargando SFace...
  curl.exe -fsSL -o "backend\data\models\face_recognition_sface_2021dec.onnx" "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
)

if not exist ".env" (
  copy /Y "env.portable.example" ".env" >nul
  echo         Archivo .env creado (PIN prueba: vigiepp / porteria)
)

echo.
echo  ========================================
echo   Instalacion OK
echo   Ejecute INICIAR.bat para abrir VigiEPP + Forense
echo  ========================================
echo.
pause
