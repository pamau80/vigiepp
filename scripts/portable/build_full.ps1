# Genera VigiEPP.exe (un solo archivo) + ZIP de respaldo
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "=== Build portable COMPLETO ==="
& (Join-Path $PSScriptRoot "setup.ps1") -Force

$dist = Join-Path $Root "dist"
$staging = Join-Path $dist "vigiepp-staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging, $dist | Out-Null

$excludeDirs = @(".git", ".venv", "dist", "node_modules", "tests", "forense\tests", ".cursor", "agent-tools", "hardware")
Get-ChildItem -Path $Root -Force | Where-Object { $_.Name -notin $excludeDirs } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $staging $_.Name) -Recurse -Force
}

Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $staging "portable\temp") -ErrorAction SilentlyContinue
Get-ChildItem (Join-Path $staging "portable\logs") -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force

# LEEME minimo
@(
    "DOBLE CLIC en VigiEPP.bat"
    "Para cerrar: CERRAR VigiEPP.bat"
    "Sin admin. Sin instalar nada."
) | Set-Content (Join-Path $staging "LEEME.txt") -Encoding UTF8

Get-ChildItem -Path $staging -Filter "*.vbs" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue

$zipLite = Join-Path $dist "vigiepp-portable-full.zip"
if (Test-Path $zipLite) { Remove-Item $zipLite -Force }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipLite -CompressionLevel Optimal

# VigiEPP.exe = 7-Zip SFX (un solo archivo para el usuario)
$sevenZ = @(
    "${env:ProgramFiles}\7-Zip\7z.exe",
    "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$outExe = Join-Path $dist "VigiEPP.exe"
if ($sevenZ) {
    $archive7z = Join-Path $dist "vigiepp.7z"
    if (Test-Path $archive7z) { Remove-Item $archive7z -Force }
    & $sevenZ a -mx9 $archive7z (Join-Path $staging "*") | Out-Null

    $sfx = Join-Path $Root "portable\sfx\config.txt"
    $sfxModule = Join-Path (Split-Path $sevenZ -Parent) "7zSD.sfx"
    if (-not (Test-Path $sfxModule)) { $sfxModule = Join-Path (Split-Path $sevenZ -Parent) "7zS2.sfx" }
    if (-not (Test-Path $sfxModule)) {
        $sfxModule = Join-Path $dist "7zSD.sfx"
        if (-not (Test-Path $sfxModule)) {
            Write-Host "Descargando modulo 7zSD.sfx ..."
            curl.exe -fsSL -o $sfxModule "https://www.7-zip.org/a/7zSD.sfx"
        }
    }

    if (Test-Path $sfxModule) {
        if (Test-Path $outExe) { Remove-Item $outExe -Force }
        $bytes = [IO.File]::ReadAllBytes($sfxModule) + [IO.File]::ReadAllBytes($sfx) + [IO.File]::ReadAllBytes($archive7z)
        [IO.File]::WriteAllBytes($outExe, $bytes)
        Remove-Item $archive7z -Force
        $exeMb = [math]::Round((Get-Item $outExe).Length / 1MB, 1)
        Write-Host "OK: $outExe ($exeMb MB)  <- DOBLE CLIC AQUI"
    } else {
        Write-Host "AVISO: modulo SFX no encontrado; solo ZIP."
    }
} else {
    Write-Host "AVISO: 7-Zip no instalado; solo ZIP."
}

Remove-Item -Recurse -Force $staging
$zipMb = [math]::Round((Get-Item $zipLite).Length / 1MB, 1)
Write-Host "OK: $zipLite ($zipMb MB)"
Write-Host "Usuario: doble clic VigiEPP.exe -> se abre el navegador. Sin admin."
