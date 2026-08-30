# Runbook — backup y restore (edge)

**Alcance:** datos locales en `VIGIEPP_DATA_DIR` (workers, rostros, config).

---

## 1. Qué respaldar

| Ruta relativa | Contenido |
|---------------|-----------|
| `workers.json` | Personas enroladas |
| `faces/` | Fotos y embeddings |
| `zones.json` | Zonas de faena |
| `cameras.json`, `nvr_devices.json` | Dispositivos |
| `notifications.json` | Alertas |
| `audit.jsonl` | Bitácora |
| `privacy.json` | Retención / QR-only |
| `.secrets_key` | Solo si no usás `VIGIEPP_SECRETS_KEY` en env |

---

## 2. Export manual (UI)

1. Login **admin**
2. Personas → **Exportar backup** (ZIP)
3. Copiar el ZIP fuera del servidor (USB, NAS, SFTP)

Equivalente API: `GET /api/identity/backup` (requiere sesión admin).

---

## 3. Restore

1. Login admin
2. Personas → **Importar backup**
3. Elegir modo:
   - **merge** — combina con datos actuales
   - **replace** — reemplaza todo (destructivo)

API: `POST /api/identity/backup/restore` multipart con `file` y `mode`.

**Antes de `replace`:** exportá un backup de seguridad.

---

## 4. Cron sugerido (Linux)

```bash
# /etc/cron.weekly/vigiepp-backup
curl -sS -b /path/admin.cookie -o /backup/vigiepp-$(date +%F).zip \
  http://127.0.0.1:8000/api/identity/backup
find /backup -name 'vigiepp-*.zip' -mtime +30 -delete
```

Alternativa: copiar volumen Docker `vigiepp-data` con `docker run --volumes-from`.

---

## 5. Verificación post-restore

```bash
curl -s http://127.0.0.1:8000/api/health | jq .gallery_size
curl -s -H "X-VigiEPP-Key: $TOKEN" http://127.0.0.1:8000/api/identity/workers | jq '.workers | length'
```

Smoke UI: identificar una persona conocida en Monitoreo.

---

## 6. Render / cloud demo

Si usás HuggingFace durable (`VIGIEPP_HF_TOKEN`), el push es automático vía `cloud_persist.py`.  
Para faena real: **backup ZIP local** sigue siendo la fuente de verdad.
