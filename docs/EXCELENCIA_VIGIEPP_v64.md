# Excelencia VigiEPP v64 — posicionamiento único

**Build:** `v64` · **Fecha:** 2026-08-30  
**Audiencia:** decisores técnicos, prevención de riesgos, TI faena

---

## Propuesta de valor en una línea

**VigiEPP es el único edge que une portería biométrica, verificación EPP, vigilancia de conductas inseguras (SIF) y workflow EHS en una sola plataforma on-prem — sin enviar video ni rostros a la nube.**

---

## Los 7 diferenciadores únicos

| # | Diferenciador | Por qué es único |
|---|---------------|------------------|
| 1 | **Portería EPP + rostro** | Misma cámara valida identidad y equipo. Competidores enterprise separan EHS (nube) de control de acceso. |
| 2 | **22 presets Acciones** | Línea de fuego, proximidad calibrada en metros, celular, humo, soldadura — editor por cámara. |
| 3 | **Workflow EHS local** | Incidentes abierto → cerrado → verificado + push a SafetyCloud/SAP/webhook. |
| 4 | **Salidas físicas nativas** | ESP32, Modbus, Wiegand — cierra el loop alarma/torniquete sin integrador. |
| 5 | **NVR industrial** | Dahua/Hikvision, barrido masivo, zonas por cámara. |
| 6 | **Forense aislado** | Producto premium post-incidente (`:8001`) sin tocar operación diaria. |
| 7 | **Soberanía Chile/LATAM** | RUT, perfiles minería/portuario/construcción, datos en LAN. |

---

## Verificación técnica (`/api/health`)

```bash
curl -s http://127.0.0.1:8000/api/health | jq '.excellence'
```

Respuesta esperada v64:

```json
{
  "tier": "edge_sovereign",
  "edge_score": 9.0,
  "capabilities": {
    "actions_presets": 22,
    "ehs_workflow": true,
    "biometric_gate": true,
    ...
  }
}
```

---

## Cadena de producto v64

```
v59 UI profesional
  → v60 wizard día cero + skins
    → v61 pestaña Acciones
      → v62 Acciones P1 (metros, cámara, editor)
        → v63 Acciones P2/P3 + EHS workflow
          → v64 excelencia + HA documentado + CI verde
```

**Forense** (paralelo): producto aislado P0–P4 en puerto 8001.

---

## Cuándo VigiEPP es la mejor opción

- Faena con **portería física** y necesidad de identificar trabajadores
- **LAN cerrada** — video y biometría no pueden salir
- Presupuesto **edge** vs contrato enterprise 5–15× mayor
- Necesidad de **acciones inmediatas** (alarma, torniquete) además de dashboard
- Chile/LATAM: RUT, comité paritario, perfiles de faena locales

## Cuándo considerar Intenseye / viAct

- Corporación **multi-planta global** con equipo EHS centralizado
- Catálogo **50+ detecciones** out-of-the-box sin teach
- SaaS con app móvil y workflows cerrados en nube

---

## Documentación de excelencia

| Documento | Contenido |
|-----------|-----------|
| `docs/RUNBOOK_HA_EDGE.md` | HA 2 nodos activo-pasivo |
| `docs/RUNBOOK_DEPLOY_EDGE.md` | Despliegue día cero |
| `docs/ENTERPRISE_AUDIT_v64.md` | Seguridad P0/P1/P2 |
| `docs/INFORME_AVANCES_RANKING_v64.md` | Ranking competitivo |
| `forense/README.md` | Producto Forense aislado |

---

*VigiEPP v64 — Excelencia edge soberana. #1 nicho portería integrada.*
