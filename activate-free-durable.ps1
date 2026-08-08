# Activa volumen durable GRATIS (Hugging Face) en Render Free — sin pagar Starter.
#
# 1) Creá cuenta gratis en https://huggingface.co/join
# 2) Token Write: https://huggingface.co/settings/tokens
# 3) Ejecutá este script y pegá el token + tu usuario HF
#
# El script configura env en Render y dispara redeploy.

$ErrorActionPreference = "Stop"
$ServiceId = "srv-d9r5qofavr4c73c9oaf0"
$ApiBase = "https://api.render.com/v1"

$Key = $env:RENDER_API_KEY
if (-not $Key) { $Key = Read-Host "RENDER_API_KEY" }
if (-not $Key) { throw "Falta RENDER_API_KEY" }

Write-Host ""
Write-Host "Abrí https://huggingface.co/settings/tokens y creá un token (Write)." -ForegroundColor Cyan
Start-Process "https://huggingface.co/settings/tokens"
$HfToken = Read-Host "HF_TOKEN (hf_...)"
$HfUser = Read-Host "Tu usuario de Hugging Face (ej. pedro123)"
if (-not $HfToken -or -not $HfUser) { throw "Faltan token o usuario" }

$Repo = "$HfUser/vigiepp-data"
$Headers = @{
  Authorization  = "Bearer $Key"
  Accept         = "application/json"
  "Content-Type" = "application/json"
}

function Set-Env([string]$Name, [string]$Value) {
  $body = @{ value = $Value } | ConvertTo-Json -Compress
  Invoke-RestMethod -Method PUT -Uri "$ApiBase/services/$ServiceId/env-vars/$Name" -Headers $Headers -Body $body | Out-Null
  Write-Host "  OK $Name"
}

Write-Host "Configurando Render Free con volumen HF ($Repo)..."
Set-Env "VIGIEPP_HF_TOKEN" $HfToken
Set-Env "HF_TOKEN" $HfToken
Set-Env "VIGIEPP_HF_REPO" $Repo
Set-Env "VIGIEPP_HF_FILE" "identity-backup.zip"
Set-Env "VIGIEPP_EPHEMERAL" "1"
Set-Env "VIGIEPP_DATA_DIR" "/data"

Write-Host "Redeploy..."
try {
  Invoke-RestMethod -Method POST -Uri "$ApiBase/services/$ServiceId/deploys" -Headers $Headers -Body '{"clearCache":"clear"}' | Out-Null
} catch {
  Invoke-RestMethod -Method POST -Uri "$ApiBase/services/$ServiceId/deploys" -Headers $Headers | Out-Null
}

Write-Host ""
Write-Host "Listo. Sin pagar Render Starter." -ForegroundColor Green
Write-Host "Tras el deploy, enrolá personas: se guardan en HF y sobreviven al sleep."
Write-Host "Health: cloud_backup.configured=true y data_persistent=true"
Write-Host ""
