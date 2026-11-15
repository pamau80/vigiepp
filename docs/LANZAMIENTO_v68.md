# Lanzamiento comercial VigiEPP v68 — edge / on-prem

**Estado:** publicado para **piloto comercial edge** (APTO CON OBSERVACIONES).  
**Fecha campaña:** AUD-VIG-2026-10-22 · build `v68`

## Alcance del lanzamiento

| Incluido | Fuera de alcance |
|----------|------------------|
| Edge faena (Docker Compose / LAN) | SaaS multi-tenant público |
| VigiEPP portería + NVR + Acciones + EHS | Sync cloud como pilar |
| Forense `:8001` con licencia edge | Billing / organizaciones |

## Cómo desplegar (faena piloto)

1. Seguir [`RUNBOOK_DEPLOY_EDGE.md`](RUNBOOK_DEPLOY_EDGE.md) (checklist día cero).
2. Completar ítems de cliente en [`auditoria_lanzamiento_2026-10/11_CHECKLIST_LANZAMIENTO.md`](auditoria_lanzamiento_2026-10/11_CHECKLIST_LANZAMIENTO.md).
3. Emitir licencia Forense: [`FORENSE_LICENSE_EDGE.md`](FORENSE_LICENSE_EDGE.md).
4. Verificar: `curl -s http://127.0.0.1:8000/api/health | jq '.build, .excellence.release'`

## Evidencia de calidad

- Auditoría integral: [`auditoria_lanzamiento_2026-10/`](auditoria_lanzamiento_2026-10/)
- Informe ejecutivo GO: madurez orientativa **78/100**, 0 CRIT / 0 HIGH abiertos
- CI: Ruff, Bandit, ESLint, pytest, E2E Playwright, **docker-edge** (build + smoke health)

## Condiciones del piloto

- PINs distintos a defaults; `VIGIEPP_SECRETS_KEY` Fernet
- Volumen persistente; HTTPS + HSTS en producción
- Paquete legal privacidad biométrica **antes de facturar**
- Un worker Uvicorn (ver runbook)

## Roadmap post-lanzamiento

Ver [`auditoria_lanzamiento_2026-10/13_ROADMAP_MEJORA_CONTINUA.md`](auditoria_lanzamiento_2026-10/13_ROADMAP_MEJORA_CONTINUA.md).
