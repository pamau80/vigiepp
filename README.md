# VigiEPP

Detección de EPP e identidad para faenas en Chile. Cámara o NVR → IA → cumplimiento, enrolamiento, informes y alerta (incluida baliza ESP32).

Build actual: **v35**. Backend FastAPI + frontend estático. Demo comercial pensada para portería y supervisor.

## Qué hace

- **Monitoreo:** webcam, cámara IP/RTSP o foto. Perfiles de faena (construcción, minería, portuario, escuela, general) con EPP obligatorio configurable.
- **Personas:** enrolamiento facial (4 poses, liveness, consentimiento Ley 19.628 / DS 44), QR y RUT.
- **Portería:** kiosco a pantalla completa. El operador solo ve monitoreo.
- **Informes:** safety score, ranking, CSV, informe imprimible, notificaciones.
- **Ropa / EPP:** enseñar prendas propias y activar un modelo custom.
- **Alarma:** ESP32 + relé (sirena / baliza) en la misma LAN.

## Demo rápida

PIN de fábrica (solo local / Cloud Agent, cambialos en producción):

| Rol | PIN |
| --- | --- |
| Administrador | `vigiepp` |
| Operador / portería | `porteria` |

1. Abrí la app (puerto **8000**).
2. Entrá con el PIN admin.
3. **1 · Monitoreo** → Iniciar cámara, o **Foto** para un JPG.
4. **2 · Personas** → marcá consentimiento → 4 poses o fotos adjuntas.
5. **5 · Informes** → Safety Score y exportar CSV / consentimiento.

La barra naranja avisa si seguís con PIN de fábrica. En Render Free también avisa si falta el backup durable.

## Arranque local

Requisitos: Python 3.12, ~2 GB RAM, webcam opcional.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
bash .cursor/install.sh     # venv + pesos YOLO / YuNet / SFace (idempotente)
```

```bash
cd backend
VIGIEPP_DOCS=1 ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrí [http://127.0.0.1:8000](http://127.0.0.1:8000). Docs: `/docs` si `VIGIEPP_DOCS=1`.

En Windows hay atajos: `start-edge.bat` (datos en disco) y `deploy-local-and-web.bat`.

## Cloud Agent (Cursor)

El repo trae `.cursor/environment.json` + `.cursor/install.sh`. El install crea `.venv` y descarga los pesos. El terminal **backend** levanta uvicorn en `:8000`.

```bash
python -m unittest discover -s backend/tests -v
```

## Despliegue en Render Free

`render.yaml` + `Dockerfile`. Health check: `/api/health`.

En el dashboard definí **sí o sí**:

- `VIGIEPP_ADMIN_PIN`
- `VIGIEPP_OPERATOR_PIN`
- `VIGIEPP_COOKIE_SECURE=1`

Render Free se duerme a los ~15 min. El workflow `.github/workflows/keepalive.yml` pega `/api/health` cada 10 minutos (ajustá la URL si no es `vigiepp.onrender.com`).

El disco de Free se borra. Para que las personas sobrevivan al sleep, volumen durable **gratis** en Hugging Face:

```powershell
# activate-free-durable.ps1  →  VIGIEPP_HF_TOKEN + VIGIEPP_HF_REPO
```

Tras el deploy, `/api/health` debe mostrar `cloud_backup.configured: true` y `data_persistent: true`.

## Consentimiento y backup

- Enrolar exige la casilla de consentimiento. Queda fecha + versión en cada ficha.
- **Personas → Exportar consentimiento** baja un CSV de auditoría.
- **Exportar backup / Restaurar** guarda o recupera personas, fotos, zonas, cámaras y notificaciones.

## Alarma ESP32

Ver `hardware/esp32-alarm/README.md`. VigiEPP debe correr en la **misma LAN** que el ESP32 (un PC edge o `start-edge.bat`). Si solo está en la nube, no alcanza la IP local.

## API útil

| Método | Ruta | Notas |
| --- | --- | --- |
| GET | `/api/health` | `model_ready`, `identity_ready`, `default_pins`, `hosted_on_render` |
| POST | `/api/auth/login` | `{ "pin": "..." }` · máx. 8 intentos / 5 min |
| POST | `/api/detect` | `file` + `profile` (multipart) |
| POST | `/api/identity/enroll` | `consent=true` obligatorio para rostro nuevo |
| GET | `/api/identity/consent.csv` | auditoría biométrica (admin) |
| GET | `/api/reports/stats` | KPIs del rango |

Auth: cookie `vigiepp_session` o header `X-VigiEPP-Key`.

## Variables de entorno

Copia `.env.example`. Las importantes:

| Variable | Para qué |
| --- | --- |
| `VIGIEPP_ADMIN_PIN` / `VIGIEPP_OPERATOR_PIN` | PIN reales (no dejes los de fábrica) |
| `VIGIEPP_AUTH` | `1` (default) / `0` para desactivar login |
| `VIGIEPP_COOKIE_SECURE` | `1` en HTTPS (Render) |
| `VIGIEPP_DATA_DIR` | disco persistente (`/data` en Docker) |
| `VIGIEPP_EPHEMERAL` | `1` en Render Free si el disco no dura |
| `VIGIEPP_HF_TOKEN` / `VIGIEPP_HF_REPO` | backup durable en Hugging Face |
| `VIGIEPP_DOCS` | `1` para `/docs` |
| `VIGIEPP_IMGSZ_MAX` | tope de inferencia (default 256 en Free) |

## Hardware y Docker

```bash
docker compose up --build
```

PIN por defecto del compose: `changeme-admin` / `changeme-porteria` (mejor pasalos por env).
