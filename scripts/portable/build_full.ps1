# Genera vigiepp-portable-full.zip — TODO incluido, sin admin, sin internet al usar
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "=== Build portable COMPLETO (para PCs restringidos) ==="
& (Join-Path $PSScriptRoot "setup.ps1") -Force

$dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
$outZip = Join-Path $dist "vigiepp-portable-full.zip"
if (Test-Path $outZip) { Remove-Item $outZip -Force }

$staging = Join-Path $dist "vigiepp-portable-full"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$excludeDirs = @(".git", ".venv", "dist", "node_modules", "tests", "forense\tests", ".cursor", "agent-tools", "hardware")
$excludeNames = @("__pycache__", ".pyc")

Get-ChildItem -Path $Root -Force | Where-Object {
    $n = $_.Name
    $n -notin $excludeDirs
} | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $staging $_.Name) -Recurse -Force
}

# Limpiar basura del staging
Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $staging "portable\temp") -ErrorAction SilentlyContinue
Get-ChildItem (Join-Path $staging "portable\logs") -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $outZip -CompressionLevel Optimal
Remove-Item -Recurse -Force $staging

$mb = [math]::Round((Get-Item $outZip).Length / 1MB, 1)
Write-Host ""
Write-Host "OK: $outZip ($mb MB)"
Write-Host "Copiar a USB / Escritorio, descomprimir, doble clic VigiEPP.bat"
Write-Host "No requiere admin ni instalar nada en el PC."
