# 05 — Auditoría de datos e integridad

## Modelo

**No hay motor SQL.** Persistencia file-based en `VIGIEPP_DATA_DIR` con locks threading en módulos críticos (`auth.py`, `privacy.py`, `identity.py`).

## Archivos principales

| Archivo | Contenido | Integridad |
|---------|-----------|------------|
| `workers.json` + `faces/` | Identidad facial | Restore vía zip backup (`backup.py`, tests restore) |
| `scan_events.jsonl` | Eventos barrido | Purga retención (`scanlog.purge_older_than`) |
| `audit.jsonl` | Bitácora admin | Export CSV API |
| `sites.json` | Multi-faena local | Cambio sitio activo API |
| `sessions.json` | Tokens sesión | Expiración 12h, purge en memoria |

## Transacciones y concurrencia

- Escrituras JSON típicamente **read-modify-write** bajo `threading.Lock` por módulo.
- **Riesgo residual:** dos procesos uvicorn sin lock inter-proceso → corrida (edge debe **un** worker o volumen con locking externo). Ver AUD-VIG-020.

## Backup / restore

- API `/api/identity/backup` + restore probada en `test_api_full_coverage.py` (zip).
- Runbook edge: volumen Docker `vigiepp-data`.

## Retención y privacidad

- `privacy.json`: retención 7–365 días, modo QR-only Ley 21.719 referenciado en UI.
- `apply_retention()` elimina JPG evidencia antigua + líneas jsonl.

## Migraciones

No aplican (sin esquema SQL). Cambios de formato JSON tolerados con defaults en lectura.

## Verificado / no verificado

| Control | Estado |
|---------|--------|
| Restore backup sintético | Verificado (pytest) |
| Restore ante corte de energía | No simulado |
| Procedimiento DR off-site | Documentado parcialmente en runbook; no probado |
| Aislamiento multi-cliente cloud | N/A (producto edge) |

## Hallazgos

| ID | Sev | Descripción |
|----|-----|-------------|
| AUD-VIG-020 | MED | Multi-worker sin coordinación de archivos JSON | Mitigación: 1 réplica edge o documentar single-worker |
