# 03 — Auditoría de seguridad

Referencias: OWASP Top 10, API Security, controles en `tests/test_security_audit.py`.

## Resumen

| Severidad | Cantidad | Bloqueo lanzamiento |
|-----------|----------|---------------------|
| CRIT | 0 | — |
| HIGH | 0 abiertos | — |
| MED | 1 cerrado | — |
| LOW | 2 | No |
| INFO | 4 | No |

## Hallazgos

| ID | Sev | Tema | Evidencia | Estado |
|----|-----|------|-----------|--------|
| AUD-VIG-001 | MED | `scripts/probar.sh` abortaba con `pipefail` si puerto libre (`lsof` exit 1) | Repro bash + fix `|| true` | **Corregido v68** |
| AUD-VIG-002 | MED | CSP bloqueaba Google Fonts → estilos degradados / violaciones consola | `security_headers.py`, computer-use `11-console-errors.webp` | **Corregido v68** |
| AUD-VIG-003 | LOW | PIN default `vigiepp`/`porteria` si env vacío | `auth.py`, bloqueado en cloud `test_default_pins_blocked_on_cloud` | Mitigado en prod vía runbook |
| AUD-VIG-004 | LOW | Sesiones persistidas en disco sin rotación automática de archivo | `sessions.json` | Aceptable edge; proteger permisos `/data` |
| AUD-VIG-005 | INFO | Sin rate limit global HTTP (sí límite body 12MB, login rate limit) | `request_limits.py`, `auth.py` LOGIN_MAX | Mejora 30d |
| AUD-VIG-006 | INFO | CSRF: API usa header/cookie custom, same-origin PWA | Diseño edge LAN | Documentar |
| AUD-VIG-007 | INFO | `pip-audit` requirements sin CVE conocidos | Comando auditoría 2026-10-22 | OK |
| AUD-VIG-008 | INFO | Bandit `-lll` sin hallazgos | CI + auditoría local | OK |

## Controles verificados (muestra)

- **SSRF RTSP:** bloqueo loopback, metadata hosts, LAN en cloud (`rtsp_security.py`)
- **Broken access control:** RBAC operador (`test_operator_access.py`, 8 tests)
- **Secretos EHS:** cifrado en disco (`test_ehs_secrets_encrypted_on_disk`)
- **Headers:** CSP nonce, nosniff, frame deny (`test_security_headers_present`)
- **Métricas:** no públicas en cloud salvo flag (`test_metrics_not_public_on_cloud`)
- **OIDC callback:** no expone sesión sin code válido

## No ejecutado

- Pentest externo, fuzzing, escaneo dependencias npm (solo ESLint)
- Revisión historial git por secretos (muestreo manual: usar `gitleaks` en CI recomendado)

## Clasificación residual

Sin vulnerabilidad **crítica explotable** demostrada en entorno de prueba con suite P0/P1 existente.
