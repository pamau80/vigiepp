# 10 — Riesgos residuales

| ID | Riesgo | Impacto | Prob. | Mitigación | Responsable propuesto |
|----|--------|---------|-------|------------|------------------------|
| AUD-VIG-020 | Corrupción JSON multi-proceso | Alto datos | Baja si 1 worker | Documentar single worker; healthcheck | DevOps edge |
| AUD-VIG-050 | Brecha legal biométrica | Legal/reputación | Media sin DPIA | Asesoría legal + políticas | Legal/Producto |
| AUD-VIG-003 | PIN débil en faena | Acceso no autorizado | Media usuario | Runbook PIN ≥8, rotación | Cliente / CS |
| AUD-VIG-005 | DoS aplicación | Disponibilidad | Media exposición LAN | Rate limit + WAF LAN | Ingeniería 60d |
| AUD-VIG-070 | RTSP credenciales NVR filtradas | Video LAN | Baja | Fernet `VIGIEPP_SECRETS_KEY` obligatorio | Cliente |
| AUD-VIG-071 | Forense con licencia `dev` | Uso no licenciado | Alta en prod | `issue_forense_license.py` | Comercial |
| AUD-VIG-072 | Dependencia Ultralytics/CVE futuros | Seguridad | Media | pip-audit en CI mensual | DevOps |

Ningún riesgo residual clasificado como **bloqueo crítico** tras controles edge documentados y suite de pruebas verde.
