# VigiEPP — arma runtime portable LOCAL (sin admin, sin tocar el sistema)
param([switch]$Force)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

$RuntimeDir = Join-Path $Root "portable\runtime\python"
$PyExe = Join-Path $RuntimeDir "python.exe"
$ReadyFlag = Join-Path $Root "portable\runtime\.ready"
$TempDir = Join-Path $Root "portable\temp"
$EmbedVersion = "3.12.8"
$EmbedUrl = "https://www.python.org/ftp/python/$EmbedVersion/python-$EmbedVersion-embed-amd64.zip"

New-Item -ItemType Directory -Force -Path $TempDir, (Join-Path $Root "portable\logs") | Out-Null
$env:TMP = $TempDir
$env:TEMP = $TempDir
$env:PYTHONNOUSERSITE = "1"
$env:PIP_NO_CACHE_DIR = "1"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

function Ensure-EmbeddedPython {
    if ((Test-Path $PyExe) -and -not $Force) { return }

    Write-Host "[1/4] Python embebido en portable\runtime\python ..."
    if (Test-Path $RuntimeDir) { Remove-Item -Recurse -Force $RuntimeDir }
    New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

    $zipPath = Join-Path $TempDir "python-embed.zip"
    curl.exe -fsSL -o $zipPath $EmbedUrl
    Expand-Archive -Path $zipPath -DestinationPath $RuntimeDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    $pth = Get-ChildItem $RuntimeDir -Filter "python*._pth" | Select-Object -First 1
    if ($pth) {
        @("python312.zip", ".", "Lib\site-packages", "import site") | Set-Content -Path $pth.FullName -Encoding ASCII
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeDir "Lib\site-packages") | Out-Null

    Write-Host "[2/4] pip local ..."
    $getPip = Join-Path $TempDir "get-pip.py"
    curl.exe -fsSL -o $getPip "https://bootstrap.pypa.io/get-pip.py"
    & $PyExe $getPip -q
}

function Fetch-Model($Url, $Dest) {
    $dir = Split-Path $Dest -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if ((Test-Path $Dest) -and ((Get-Item $Dest).Length -gt 1000)) { return }
    Write-Host "       $(Split-Path $Dest -Leaf) ..."
    curl.exe -fsSL -o $Dest $Url
}

if ((Test-Path $ReadyFlag) -and (Test-Path $PyExe) -and -not $Force) {
    Write-Host "Runtime portable OK."
    exit 0
}

Ensure-EmbeddedPython

Write-Host "[3/4] Librerias dentro de la carpeta portable (sin instalar en Windows) ..."
& $PyExe -m pip install --upgrade pip -q
& $PyExe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu -q
& $PyExe -m pip install -r (Join-Path $Root "backend\requirements.txt") -q
& $PyExe -m pip install -r (Join-Path $Root "forense\requirements.txt") -q

Write-Host "[4/4] Modelos IA ..."
$models = Join-Path $Root "backend\models"
$faceModels = Join-Path $Root "backend\data\models"
New-Item -ItemType Directory -Force -Path $models, $faceModels, (Join-Path $Root "backend\data\faces"), (Join-Path $Root "forense\data") | Out-Null

Fetch-Model "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt" (Join-Path $models "best_ppe.pt")
Fetch-Model "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" (Join-Path $faceModels "face_detection_yunet_2023mar.onnx")
Fetch-Model "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" (Join-Path $faceModels "face_recognition_sface_2021dec.onnx")

New-Item -ItemType File -Force -Path $ReadyFlag | Out-Null
Write-Host "Listo."
exit 0
