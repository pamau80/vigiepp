# Excelencia VigiEPP v66 — RBAC UI sincronizado

**Build:** `v66` · **Base:** v65 (RBAC API + CSP + watchdog)

---

## Qué aporta v66

| Capa | v65 | v66 |
|------|-----|-----|
| API RBAC | `rbac.py` middleware | `/api/auth/me` expone `rbac` |
| UI operador | CSS oculta pestañas | `data-rbac-admin` + secciones enterprise ocultas |
| HA | Watchdog check | Webhook `ALERT_WEBHOOK_URL` opcional |

---

## Verificación

```bash
# Sesión operador
curl -s -H "X-VigiEPP-Key: $TOKEN" http://127.0.0.1:8000/api/auth/me | jq '.role, .rbac.admin'

# Health
curl -s http://127.0.0.1:8000/api/health | jq '.build, .excellence.edge_score'
```

---

*VigiEPP v66 — excelencia edge soberana con RBAC de punta a punta.*
