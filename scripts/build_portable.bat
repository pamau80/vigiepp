@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist dist mkdir dist
echo Empaquetando vigiepp-portable.zip ...
powershell -NoProfile -Command ^
  "$root = Get-Location; $dest = Join-Path $root 'dist\vigiepp-portable.zip';" ^
  "$exclude = @('.git','.venv','node_modules','__pycache__','dist','.cursor','tests','forense\tests','backend\runs','backend\datasets');" ^
  "$files = Get-ChildItem -Path $root -Recurse -File | Where-Object {" ^
  "  $rel = $_.FullName.Substring($root.Path.Length + 1);" ^
  "  -not ($exclude | Where-Object { $rel -like \"$_*\" -or $rel -like \"*\$_\*\" })" ^
  "};" ^
  "if (Test-Path $dest) { Remove-Item $dest -Force };" ^
  "Compress-Archive -Path ($files | ForEach-Object { $_.FullName }) -DestinationPath $dest -CompressionLevel Optimal"
echo.
echo Listo: dist\vigiepp-portable.zip
echo Copia el ZIP, descomprime y doble clic en VigiEPP.bat
pause
