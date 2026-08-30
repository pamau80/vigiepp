# Guía para probar VigiEPP (v67 + Forense)

**Tiempo estimado:** 5–10 minutos · **Requisitos:** Python 3.12, navegador Chrome

---

## 1. Arranque en un comando

```bash
bash .cursor/install.sh    # solo la primera vez (venv + modelos IA)
bash scripts/probar.sh     # levanta :8000 y :8001
```

Deberías ver:

```
VigiEPP listo para probar — build v67
App:     http://127.0.0.1:8000/
Forense: http://127.0.0.1:8001/
PIN admin: vigiepp · PIN portería: porteria
```

---

## 2. VigiEPP core (`:8000`)

### Login

| Rol | PIN | Qué verás |
|-----|-----|-----------|
| **Admin** | `vigiepp` | Todas las pestañas (Vivo, Masivo, Personas, EPP, Acciones, Config, Informes) |
| **Portería** | `porteria` | Solo monitoreo en vivo (modo kiosk) |

### Checklist rápido (admin)

1. **http://127.0.0.1:8000/** → login con `vigiepp`
2. **Vivo** → Iniciar cámara → ver detección EPP (puede tardar ~10 s en cargar modelo)
3. **Personas** → enrolar rostro de prueba (webcam)
4. **Acciones** → ver presets (22+) y historial de eventos
5. **Config → Enterprise** → workflow EHS (incidentes abierto/cerrado/verificado)
6. **API health:**
   ```bash
   curl -s http://127.0.0.1:8000/api/health | jq '.build, .excellence.edge_score, .identity_ready'
   ```

### Checklist portería

1. Logout → login con `porteria`
2. Solo pestaña **Vivo** visible, modo kiosk
3. API bloqueada para admin:
   ```bash
   TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
     -H 'Content-Type: application/json' -d '{"pin":"porteria"}' | jq -r .token)
   curl -s -o /dev/null -w "%{http_code}" -H "X-VigiEPP-Key: $TOKEN" \
     http://127.0.0.1:8000/api/identity/workers
   # esperado: 403
   ```

---

## 3. Forense (`:8001`)

Producto **aislado** — no toca la UI de VigiEPP.

1. **http://127.0.0.1:8001/** → mismo PIN admin `vigiepp`
2. Subir un video corto (MP4) o usar muestra
3. Crear job de análisis → ver informe, heatmap, export PDF
4. Health:
   ```bash
   curl -s http://127.0.0.1:8001/api/forense/health | jq .
   ```

---

## 4. Métricas y HA (opcional)

```bash
# Gauges readiness (watchdog / Grafana)
curl -s http://127.0.0.1:8000/metrics | grep vigiepp_edge_ready

# Watchdog (simula check)
PRIMARY_HOST=127.0.0.1 PORT=8000 bash scripts/vigiepp-watchdog.sh --check-only
```

---

## 5. Tests automatizados

```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest tests/ --ignore=tests/e2e -q          # 127+ unit/API
pytest forense/tests/ -q                     # Forense
bash scripts/review_full_e2e.sh              # API smoke (servidor arriba)
```

---

## 6. Docker (edge faena)

```bash
cp .env.example .env   # editar PINs
docker compose up -d --build
```

---

## 7. Problemas frecuentes

| Síntoma | Solución |
|---------|----------|
| `identity_ready: false` | Esperar 30–90 s tras arranque (precarga YuNet/SFace) |
| Puerto 8000 ocupado | `bash scripts/probar.sh` lo libera automáticamente |
| Cámara no abre | Permisos del navegador; usar HTTPS solo si configuraste HSTS |
| Forense 401 | Login admin en `:8000` primero o PIN `vigiepp` en `:8001` |

---

## Builds incluidos en `main`

| Versión | Contenido |
|---------|-----------|
| v62–v66 | UI, Acciones, EHS, RBAC, CSP, watchdog |
| v67 | Métricas Prometheus readiness + HSTS edge |
| Forense | Producto `:8001` aislado P0–P4 |

*Última actualización: 2026-08-30*
