# Runbook — despliegue edge VigiEPP

**Modelo:** un servidor por faena, en la misma red LAN que NVR/cámaras.  
**Build referencia:** v55+ · **No SaaS** — datos e inferencia permanecen en sitio.

---

## 1. Requisitos

| Componente | Mínimo |
|------------|--------|
| SO | Linux (Docker) o Windows 10+ (`start-edge.bat`) |
| CPU | 4 cores (inferencia YOLO + SFace en CPU) |
| RAM | 4 GB (8 GB recomendado) |
| Disco | 10 GB persistentes (`VIGIEPP_DATA_DIR`) |
| Red | LAN hacia NVR/RTSP; HTTPS opcional vía reverse proxy |

---

## 2. Despliegue Docker (recomendado)

```bash
cp .env.example .env
# Editar PINs y VIGIEPP_DATA_DIR si aplica
docker compose up -d --build
curl -s http://127.0.0.1:8000/api/health | jq .
```

Verificar en `/api/health`:

- `identity_ready: true` (esperar ~15–60 s tras arranque)
- `data_persistent: true` en producción
- `build` coincide con versión desplegada

---

## 3. Variables críticas (producción)

```env
VIGIEPP_AUTH=1
VIGIEPP_ADMIN_PIN=<pin-fuerte-unico>
VIGIEPP_OPERATOR_PIN=<pin-guardia-porteria>
VIGIEPP_SECRETS_KEY=<fernet-key>   # credenciales NVR/EHS
VIGIEPP_DATA_DIR=/data             # volumen persistente
VIGIEPP_EPHEMERAL=0
VIGIEPP_ALLOW_DEFAULT_PINS=0
VIGIEPP_COOKIE_SECURE=1            # si hay HTTPS
```

Generar Fernet:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 4. Rotación de PIN

1. Definir nuevos `VIGIEPP_ADMIN_PIN` / `VIGIEPP_OPERATOR_PIN` en `.env`
2. Reiniciar servicio: `docker compose restart vigiepp`
3. Invalidar sesiones antiguas (opcional): borrar `{data_dir}/sessions.json`
4. Comunicar PINs por canal seguro (no email plano)
5. Verificar login admin y operador en UI

---

## 5. Backup y restore

**Export manual (admin):** Personas → backup ZIP, o `GET /api/identity/backup`

Contenido: `workers.json`, `faces/`, zonas, audit, config.

**Restore:** `POST /api/identity/backup/restore` (modo `merge` o `replace`)

**Programar:** cron semanal copiando el ZIP fuera del servidor faena.

---

## 6. RTSP / NVR

- El servidor edge **debe** estar en la LAN del NVR
- Configurar `VIGIEPP_RTSP_ALLOW` con IPs/hostnames permitidos
- Probar: `POST /api/nvr/probe` desde UI Dispositivos
- Cloud (Render) **no** sustituye edge para cámaras LAN

---

## 7. Smoke test post-deploy

```bash
bash scripts/review_e2e.sh          # requiere servidor en :8000
bash scripts/review_browser_e2e.sh    # Playwright (opcional)
```

Checklist manual:

- [ ] Login admin
- [ ] Login operador (solo monitoreo)
- [ ] Detección EPP en vivo
- [ ] Enrolar persona de prueba
- [ ] Stream RTSP (si aplica)

---

## 8. Incidentes frecuentes

| Síntoma | Causa | Acción |
|---------|-------|--------|
| `identity_ready: false` | Modelos ONNX cargando | Esperar 60 s; revisar logs uvicorn |
| 503 PIN default en cloud | PINs no configurados | Set env en host |
| RTSP 400 | URL LAN bloqueada | `VIGIEPP_ALLOW_LAN=1` + allowlist |
| Disco lleno | Evidencia / audit | `POST /api/privacy/retention/run` |

---

## 9. Actualización de versión

```bash
git pull   # o nueva imagen Docker
docker compose up -d --build
# Verificar build en /api/health
bash scripts/review_e2e.sh
```

No force-push datos de producción; backup antes de restore con `replace`.
