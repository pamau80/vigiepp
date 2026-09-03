# Runbook — despliegue edge VigiEPP

**Modelo:** un servidor por faena, en la misma red LAN que NVR/cámaras.  
**Build referencia:** v57+ · **Edge on-prem** — datos e inferencia permanecen en sitio.

Ver [RUNBOOK_ENTRENAR_EPP_FAENA.md](RUNBOOK_ENTRENAR_EPP_FAENA.md) — color/tipo de casco, ropa, lentes y guantes se entrenan en sitio (pestaña EPP).

---

| Componente | Mínimo | Recomendado faena |
|------------|--------|-------------------|
| SO | Linux (Docker) o Windows 10+ | Ubuntu 22.04 LTS / Docker Compose |
| CPU | 4 cores | 8 cores (YOLO + SFace simultáneo) |
| RAM | 4 GB | 8–16 GB |
| Disco | 10 GB persistentes | 50 GB SSD (`VIGIEPP_DATA_DIR`) |
| Red | LAN hacia NVR/RTSP | Gigabit, mismo switch que NVR |
| Pantalla portería | 1080p, Chrome/Edge | Tablet fija, modo kiosk |

---

## 2. Despliegue Docker (recomendado)

```bash
cp .env.example .env
# Editar PINs, VIGIEPP_FORENSE_LICENSE (producción) y VIGIEPP_DATA_DIR si aplica
docker compose up -d --build
curl -s http://127.0.0.1:8000/api/health | jq .
curl -s http://127.0.0.1:8001/api/forense/health | jq .
bash scripts/docker_forense_smoke.sh
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
VIGIEPP_ALLOW_LAN=1                # RTSP/NVR en LAN
VIGIEPP_RTSP_ALLOW=192.168.1.0/24  # o IPs concretas del NVR
VIGIEPP_COOKIE_SECURE=1            # si hay HTTPS
```

Generar Fernet:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 4. Checklist faena real (día cero)

### Infraestructura

- [ ] Servidor edge en **misma VLAN** que NVR y cámaras IP
- [ ] IP estática o reserva DHCP para el host Docker
- [ ] Volumen persistente montado (`vigiepp-data` o ruta local)
- [ ] Firewall: puerto **8000** (o reverse proxy 443) solo desde LAN/VPN
- [ ] UPS o protección eléctrica en gabinete/sala

### Seguridad

- [ ] PIN admin y portería **distintos**, ≥8 caracteres, no defaults
- [ ] `VIGIEPP_SECRETS_KEY` en env (no depender de `.secrets_key` auto)
- [ ] `.env` fuera de git; permisos 600 en host
- [ ] Documentar quién tiene PIN admin vs portería

### Red / video

- [ ] Ping desde servidor edge al NVR (`ping 192.168.x.x`)
- [ ] Probe NVR desde UI **Equipos** o `POST /api/nvr/probe`
- [ ] Al menos 1 canal RTSP estable 15 min sin corte
- [ ] Cámara portería USB/IP probada en **Vivo → Webcam**

### Identidad y EPP

- [ ] `identity_ready: true` en health
- [ ] Enrolar 2–3 personas prueba (admin → Personas)
- [ ] Identificación en vivo con consentimiento marcado
- [ ] Perfil faena (mandatorio EPP) configurado en Monitoreo
- [ ] Zonas dibujadas si hay áreas restringidas

### Portería

- [ ] Login operador abre **modo kiosk** (pantalla CUMPLE/NO CUMPLE)
- [ ] Salida kiosk exige **PIN admin** (probar en tablet)
- [ ] Audio alertas activadas si aplica en faena ruidosa

### Respaldo

- [ ] Export backup ZIP post-enrolamiento inicial
- [ ] Copia ZIP fuera del servidor (NAS/USB)
- [ ] Cron semanal documentado (`docs/RUNBOOK_BACKUP.md`)

### Entrega

- [ ] Capacitación 30 min: admin vs portería
- [ ] Contacto soporte y procedimiento escalamiento
- [ ] Foto/checklist firmado por jefe faena o SSOMA

---

## 5. Rotación de PIN

1. Definir nuevos `VIGIEPP_ADMIN_PIN` / `VIGIEPP_OPERATOR_PIN` en `.env`
2. Reiniciar servicio: `docker compose restart vigiepp`
3. Invalidar sesiones antiguas (opcional): borrar `{data_dir}/sessions.json`
4. Comunicar PINs por canal seguro (no email plano)
5. Verificar login admin y operador en UI

---

## 6. Backup y restore

Ver **`docs/RUNBOOK_BACKUP.md`**.

Resumen: export ZIP admin → copia off-site → restore `merge`/`replace` con precaución.

---

## 7. RTSP / NVR

- El servidor edge **debe** estar en la LAN del NVR
- Configurar `VIGIEPP_RTSP_ALLOW` con IPs/hostnames permitidos
- Probar: `POST /api/nvr/probe` desde UI Dispositivos
- Cloud (Render) **no** sustituye edge para cámaras LAN

---

---

## 8. VigiEPP Forense (`:8001`)

Producto aislado post-incidente. Requiere licencia y PIN admin.

```env
VIGIEPP_FORENSE=1
VIGIEPP_FORENSE_LICENSE=<site>.<exp>.<sig>   # ver docs/FORENSE_LICENSE_EDGE.md
VIGIEPP_FORENSE_DATA_DIR=/data/forense
```

Checklist:

- [ ] Puerto **8001** accesible solo desde LAN/VPN
- [ ] Licencia emitida con `forense/scripts/issue_forense_license.py`
- [ ] `curl -s :8001/api/forense/health` → `license.valid: true`
- [ ] Demo: `bash forense/scripts/demo_caso_completo.sh`

---

## 9. Smoke test post-deploy

```bash
bash scripts/review_e2e.sh
bash scripts/review_browser_e2e.sh   # 6 tests Playwright
npm run lint
pytest tests/ --ignore=tests/e2e -q
```

Checklist manual rápido:

- [ ] Login admin → nav completa
- [ ] Login operador → kiosk + nav oculta
- [ ] Salir kiosk con PIN admin
- [ ] Detección EPP en vivo
- [ ] Enrolar persona de prueba
- [ ] Stream RTSP (si aplica)

---

## 9. Incidentes frecuentes

| Síntoma | Causa | Acción |
|---------|-------|--------|
| `identity_ready: false` | Modelos ONNX cargando | Esperar 60 s; revisar logs uvicorn |
| 503 PIN default en cloud | PINs no configurados | Set env en host |
| RTSP 400 | URL LAN bloqueada | `VIGIEPP_ALLOW_LAN=1` + allowlist |
| Disco lleno | Evidencia / audit | `POST /api/privacy/retention/run` |
| Cámara bloqueada Chrome | Permiso denegado | Ícono candado en URL → Permitir |
| Operador ve config | Sesión admin residual | Cerrar sesión / borrar cookies |

---

## 10. Actualización de versión

```bash
git pull
docker compose up -d --build
curl -s http://127.0.0.1:8000/api/health | jq .build
bash scripts/review_e2e.sh
bash scripts/review_browser_e2e.sh
```

Backup antes de actualizar si hay cambios en esquema de datos. No usar `replace` en restore sin export previo.

---

## 11. Contactos sugeridos (plantilla faena)

| Rol | Nombre | Contacto |
|-----|--------|----------|
| Admin VigiEPP | | |
| Portería turno | | |
| Red / CCTV | | |
| SSOMA | | |
