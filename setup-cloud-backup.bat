@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  VigiEPP — respaldo cloud (para que Render Free NO pierda personas)
echo.
echo  1) En GitHub crea un repo PRIVADO, ej: vigiepp-data
echo  2) Crea un Fine-grained PAT con Contents: Read and write en ese repo
echo  3) En Render → tu servicio → Environment agregá:
echo       VIGIEPP_CLOUD_REPO = tuusuario/vigiepp-data
echo       VIGIEPP_CLOUD_TOKEN = ghp_... o github_pat_...
echo       VIGIEPP_CLOUD_PATH = vigiepp-identity-backup.zip
echo       VIGIEPP_EPHEMERAL = 1
echo  4) Redeploy / Manual Deploy
echo.
echo  Mientras tanto, el navegador ya auto-guarda un backup local (IndexedDB)
echo  y lo restaura solo si el servidor despierta vacío.
echo.
echo  Ideal a largo plazo: plan Starter + disco 2GB (como Railway antes).
echo.
pause
