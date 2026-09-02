# Runbook HA edge — 2 nodos activo/pasivo

**Modelo:** alta disponibilidad manual para faenas críticas (minería, puerto, oil & gas).  
**Build referencia:** v64+ · **RTO objetivo:** &lt; 15 min · **RPO objetivo:** &lt; 5 min (sync datos)

VigiEPP no incluye cluster automático: este runbook documenta una topología **activo-pasivo** probada en edge, alineada con soberanía de datos y sin dependencia SaaS.

---

## 1. Topología recomendada

```
                    ┌─────────────────┐
   Cámaras/NVR ────►│  Switch LAN     │
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │ Edge PRIMARY │ │  VIP DNS │ │ Edge STANDBY │
      │ vigiepp-01   │ │ (opc.)   │ │ vigiepp-02   │
      │ :8000 activo │ │          │ │ :8000 apagado│
      └──────┬───────┘ └──────────┘ └──────┬───────┘
             │                              │
             └──────────┬───────────────────┘
                        ▼
              ┌──────────────────┐
              │ Almacén compartido│
              │ NFS o rsync bidir.│
              │ VIGIEPP_DATA_DIR  │
              └──────────────────┘
```

| Rol | Host | Puerto | Estado normal |
|-----|------|--------|---------------|
| **Primary** | `vigiepp-01` (IP fija) | 8000 | Docker `up`, inferencia activa |
| **Standby** | `vigiepp-02` (IP fija) | 8000 | Docker `stopped` o health-only |
| **Datos** | NFS en NAS o rsync | — | Sync cada 1–5 min |

**Forense (opcional):** producto aislado en `:8001` solo en primary; no requiere HA para operación portería.

---

## 2. Requisitos hardware (cada nodo)

Igual que `RUNBOOK_DEPLOY_EDGE.md`, con estas adiciones:

| Componente | Primary | Standby |
|------------|---------|---------|
| CPU/RAM | 8 cores / 16 GB | 8 cores / 16 GB (misma imagen Docker) |
| Disco local | 50 GB SSD + volumen datos | 50 GB SSD (cache; datos en NFS) |
| Red | 2× GbE (opcional bonding) | Idéntica VLAN que primary |
| UPS | Obligatorio | Obligatorio |

Ambos nodos deben poder alcanzar **las mismas cámaras RTSP** y el **mismo NVR**.

---

## 3. Configuración de datos compartidos

### Opción A — NFS (recomendada)

En el NAS/servidor de archivos:

```bash
# /etc/exports (ejemplo)
/data/vigiepp  192.168.10.0/24(rw,sync,no_subtree_check,no_root_squash)
```

En **ambos** nodos edge (`/etc/fstab`):

```
nas.local:/data/vigiepp  /data/vigiepp  nfs  defaults,_netdev  0  0
```

`.env` en ambos nodos (idéntico salvo hostname):

```env
VIGIEPP_DATA_DIR=/data/vigiepp
VIGIEPP_EPHEMERAL=0
VIGIEPP_SECRETS_KEY=<misma-clave-fernet-en-ambos>
VIGIEPP_ADMIN_PIN=<mismo-pin>
```

> **Crítico:** `VIGIEPP_SECRETS_KEY` debe ser **idéntica** en primary y standby para descifrar credenciales NVR/EHS.

### Opción B — rsync (sin NAS)

Cron en primary cada 2 min hacia standby:

```bash
*/2 * * * * rsync -az --delete /data/vigiepp/ standby:/data/vigiepp/
```

RPO ≈ 2 min. Más simple; menos consistente bajo escritura intensa (enrolamientos masivos).

---

## 4. Despliegue Docker (ambos nodos)

```bash
git clone https://github.com/pamau80/vigiepp.git && cd vigiepp
cp .env.example .env
# Editar según sección 3
docker compose up -d --build   # solo en PRIMARY al inicio
```

**Standby:** clonar mismo repo y `.env`, montar mismo `VIGIEPP_DATA_DIR`, pero:

```bash
docker compose stop   # mantener imagen actualizada, servicio detenido
```

Actualizar standby mensualmente:

```bash
git pull && docker compose build --pull
# No levantar hasta failover
```

---

## 5. Health checks y monitoreo

### Endpoint local

```bash
curl -s http://127.0.0.1:8000/api/health | jq '{build, identity_ready, model_ready, data_persistent, excellence}'
```

Criterios **healthy**:

- `identity_ready: true`
- `data_persistent: true`
- `status: ok`

### Script watchdog (cron cada 60 s en un tercer host o en standby)

```bash
#!/bin/bash
# /usr/local/bin/vigiepp-watchdog.sh
PRIMARY=192.168.10.11
STANDBY=192.168.10.12
if ! curl -sf --max-time 5 "http://${PRIMARY}:8000/api/health" | jq -e '.identity_ready' >/dev/null; then
  echo "$(date -Is) PRIMARY DOWN — iniciar procedimiento failover" | tee -a /var/log/vigiepp-ha.log
  # Opcional: enviar alerta SNMP/WhatsApp
fi
```

---

## 6. Procedimiento de failover (manual)

**Cuándo:** primary sin respuesta HTTP, disco corrupto, o mantenimiento planificado.

| Paso | Acción | Responsable |
|------|--------|-------------|
| 1 | Confirmar primary caído (`ping`, `curl /api/health`) | Operaciones |
| 2 | Verificar datos en standby (`ls $VIGIEPP_DATA_DIR`) | Operaciones |
| 3 | En **standby**: `docker compose up -d` | Operaciones |
| 4 | Esperar `identity_ready: true` (≤ 90 s) | — |
| 5 | Actualizar DNS/VIP o IP en tablets portería → standby | Red |
| 6 | Probar portería: login, detect, identificar | Guardia |
| 7 | Registrar en bitácora (`/api/audit` o ticket interno) | Supervisor |
| 8 | Reparar primary; dejar como nuevo standby | Infra |

**Tiempo objetivo RTO:** 10–15 min con DNS/VIP preconfigurado.

---

## 7. Failback (volver a primary)

1. Sincronizar datos standby → primary (`rsync` o dejar NFS como fuente única).
2. Levantar Docker en primary verificado.
3. Cambiar DNS/VIP de vuelta.
4. Detener Docker en ex-standby.
5. Verificar enrolamientos y reglas Acciones.

---

## 8. Checklist excelencia HA (pre-producción)

- [ ] Misma versión Docker image en ambos nodos (`docker images | grep vigiepp`)
- [ ] `VIGIEPP_SECRETS_KEY` idéntica
- [ ] Backup diario adicional (`docs/RUNBOOK_BACKUP.md`)
- [ ] UPS probado (corte simulado 30 s)
- [ ] Failover ensayado en mesa (no solo en producción)
- [ ] Tablets portería con IP/DNS documentado para cambio rápido
- [ ] Runbook impreso en sala de control
- [ ] Contacto 24/7 de soporte interno definido

---

## 9. Limitaciones conocidas

| Limitación | Mitigación |
|------------|------------|
| Failover no automático | Watchdog + procedimiento ≤ 15 min |
| RTSP streams activos se cortan | Reconexión automática al levantar standby |
| Enrolamiento durante sync rsync | Pausar enrolamientos durante ventana de sync o usar NFS |
| Forense en :8001 | Opcional; levantar manualmente post-failover |

---

## 10. Referencias

- `docs/RUNBOOK_DEPLOY_EDGE.md` — despliegue base
- `docs/RUNBOOK_BACKUP.md` — backup identidad
- `docs/EXCELENCIA_VIGIEPP_v64.md` — diferenciadores competitivos
- `docs/ENTERPRISE_AUDIT_v64.md` — controles de seguridad

---

*VigiEPP v64 — Soberanía edge con HA documentado. Único en el segmento portería+EPP+Acciones+EHS en LAN cerrada.*
