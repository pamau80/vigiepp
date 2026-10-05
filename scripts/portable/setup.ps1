# VigiEPP portable — primera ejecución (venv, deps, modelos IA)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

function Find-Python {
    $candidates = @(
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "py"; Args = @("-3") },
        @{ Exe = "python"; Args = @() },
        @{ Exe = "python3"; Args = @() }
    )
    foreach ($c in $candidates) {
        $cmd = Get-Command $c.Exe -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $ver = & $c.Exe @($c.Args + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))
            if ($ver -match "^3\.(1[2-9]|[2-9][0-9])") {
                return @{ Exe = $c.Exe; Args = $c.Args }
            }
        } catch { }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host ""
    Write-Host "  ERROR: Necesitás Python 3.12 o superior." -ForegroundColor Red
    Write-Host "  Descargalo desde https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Durante la instalacion, marcá 'Add python.exe to PATH'." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[setup] Creando entorno virtual..."
    $venvArgs = @($py.Args + @("-m", "venv", (Join-Path $Root ".venv")))
    & $py.Exe @venvArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[setup] Instalando dependencias (puede tardar varios minutos)..."
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $venvPy -m pip install -r (Join-Path $Root "backend\requirements.txt")
& $venvPy -m pip install -r (Join-Path $Root "forense\requirements.txt")

function Fetch-Model($Url, $Dest) {
    $dir = Split-Path $Dest -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt 1000)) {
        Write-Host "[setup] ya existe $(Split-Path $Dest -Leaf)"
        return
    }
    Write-Host "[setup] descargando $(Split-Path $Dest -Leaf)..."
    curl.exe -fsSL -o $Dest $Url
}

$models = Join-Path $Root "backend\models"
$faceModels = Join-Path $Root "backend\data\models"
New-Item -ItemType Directory -Force -Path $models, $faceModels, (Join-Path $Root "backend\data\faces"), (Join-Path $Root "forense\data") | Out-Null

Fetch-Model "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt" (Join-Path $models "best_ppe.pt")
Fetch-Model "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" (Join-Path $faceModels "face_detection_yunet_2023mar.onnx")
Fetch-Model "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" (Join-Path $faceModels "face_recognition_sface_2021dec.onnx")

Write-Host "[setup] Listo."
exit 0
