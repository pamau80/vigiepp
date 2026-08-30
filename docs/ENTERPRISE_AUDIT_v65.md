# Auditoría enterprise — VigiEPP v65

**Build auditado:** `v65`  
**Fecha:** 2026-08-30  
**Rama:** `cursor/v65-excellence-8b97` · base v64

---

## Novedades v64→v65

| Componente | v64 | v65 |
|------------|-----|-----|
| RBAC API | Binario admin/operator | **Granular por sección** (`rbac.py`) |
| CSP | Estática | **Nonce por petición** |
| HA | Runbook manual | **Watchdog semi-automático** |
| Tests pytest | 115 | **124** |
| Edge score | 9.0 | **9.2** |

---

## Controles cerrados

| Control | Evidencia |
|---------|-----------|
| RBAC granular | `tests/test_rbac.py`, `tests/test_operator_access.py` |
| CSP nonce | `tests/test_csp_nonce.py` |
| Watchdog HA | `scripts/vigiepp-watchdog.sh` |
| Sin regresión P0/P1 | `tests/test_security_audit.py` |

---

## Cadena de merge

`#13` → `#15` → `#16` → **#17 (v65)**
