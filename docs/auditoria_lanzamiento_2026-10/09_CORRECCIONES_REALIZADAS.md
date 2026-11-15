# 09 — Correcciones realizadas

Build **v68** en rama `cursor/commercial-launch-audit-cfa5`.

| ID | Problema | Causa raíz | Cambio | Archivos | Regresión |
|----|----------|------------|--------|----------|-----------|
| AUD-VIG-001 | `probar.sh` fallaba al iniciar sin procesos en puerto | `set -o pipefail` + `lsof` exit 1 | `\|\| true` en captura PID | `scripts/probar.sh` | Ejecutado OK post-fix |
| AUD-VIG-002 | CSP bloqueaba Google Fonts | `font-src`/`style-src` solo `'self'` | Allowlist `fonts.googleapis.com`, `fonts.gstatic.com` | `backend/app/security_headers.py` | `test_csp_nonce.py` ampliado |
| — | Bump versión | Convención release | v67 → v68 | `core.py`, `constants.js`, `app.js`, `sw.js`, `test_api_full_coverage.py` | 127 pytest pass |

## Efectos secundarios

- Service worker cache name cambia → usuarios recargan shell PWA una vez (esperado).
- CSP ligeramente más permisiva solo para dominios Google Fonts estáticos.

## Pendientes (no corregidos en código)

- AUD-VIG-012 logout viewport
- AUD-VIG-020 multi-worker JSON
- AUD-VIG-050 paquete legal
