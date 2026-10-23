# 11 — Checklist lanzamiento

## Pre-despliegue (edge faena)

- [ ] PIN admin y portería únicos (≠ defaults)
- [ ] `VIGIEPP_SECRETS_KEY` Fernet generada
- [ ] `VIGIEPP_DATA_DIR` volumen persistente montado
- [ ] `VIGIEPP_ALLOW_LAN=1` + `VIGIEPP_RTSP_ALLOW` acotado a subnet NVR
- [ ] HTTPS reverse proxy + `VIGIEPP_COOKIE_SECURE=1` + `VIGIEPP_HSTS=1` / `VIGIEPP_EDGE=1`
- [ ] Firewall: solo LAN/VPN a 443/8000
- [ ] Licencia Forense producción emitida
- [ ] Backup inicial `identity/backup` verificado restore en staging
- [ ] Política privacidad entregada al cliente faena

## Build / CI (verificado auditoría)

- [x] Ruff + Bandit + ESLint
- [x] Pytest 127 + Forense 53
- [x] E2E browser subset 7/7
- [ ] Docker image build en pipeline (no rebuild VM auditoría)

## Post-despliegue

- [ ] `curl /api/health` → `identity_ready`, `data_persistent`
- [ ] Probar RTSP un canal real
- [ ] Enrolar 3 trabajadores piloto
- [ ] Portería kiosk 24h piloto
- [ ] Revisar `/metrics` solo interno
- [ ] Registrar versión build v68 en bitácora cliente

## Rollback

- Restaurar imagen Docker anterior + volumen snapshot
- Documentado parcialmente en `docs/RUNBOOK_DEPLOY_EDGE.md`
