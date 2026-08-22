# VigiEPP — guía para agentes y pruebas

## Cloud Agent: cómo abrir la app (importante)

**`http://127.0.0.1:8000` solo funciona dentro de la VM del agente**, no en tu PC.

Para probar desde el navegador en tu máquina:

1. Abrí la página del **agente en Cursor** (ej. `https://cursor.com/agents/<id-del-run>`).
2. Buscá la sección **Ports** / **Puertos** o el botón **Open** junto a **VigiEPP · 8000**.
3. Hacé clic ahí — Cursor abre un túnel HTTPS a la app.
4. Login PIN admin demo: `vigiepp` · operador: `porteria`.

Si no ves el puerto 8000:

- El entorno personal del repo puede no tener `ports` del `environment.json`. En **Dashboard → Cloud Agents → Environments**, editá el entorno de `pamau80/vigiepp` y asegurate de exponer el puerto **8000**, o usá el `environment.json` del repo.
- Recargá el agente o pedile al agente que ejecute: `bash .cursor/start-app.sh`
- Verificá salud: `curl http://127.0.0.1:8000/api/health` (dentro de la VM).

## Arranque manual (dentro de la VM)

```bash
bash .cursor/install.sh          # primera vez
bash .cursor/start-app.sh        # levanta uvicorn :8000
```

Con recarga en desarrollo:

```bash
cd backend && VIGIEPP_DOCS=1 ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Pruebas

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

## Demo en pantallas

| Pestaña | Qué probar |
| --- | --- |
| 1 · Monitoreo | EPP + identidad (webcam/foto) |
| 6 · Vigilancia | Timeline, filtros, RTSP, servicio 24/7 |
| 2 · Personas | Enrolamiento facial |

Build actual en rama de trabajo: ver `/api/health` → campo `build`.

## Alternativa pública (Render)

URL típica: `https://vigiepp.onrender.com` — puede ir varias versiones detrás de `main` hasta que se despliegue el PR. PIN según variables en Render (no los de fábrica si los cambiaste).

## Cursor Cloud specific instructions

- Tras cambios en `.cursor/environment.json`, hace falta **nuevo build de entorno** o agente nuevo para que `start` y `ports` apliquen en pods futuros.
- No commitear `backend/data/datasets/` ni secretos.
