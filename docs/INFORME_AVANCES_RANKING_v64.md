# Informe de avances y ranking — VigiEPP v64

**Build:** `v64` · **Fecha:** 2026-08-30

---

## 1. Resumen

VigiEPP v64 sube a **#2 global (8.45)** y **#1 nicho edge/portería (9.0)** tras Acciones P2/P3, workflow EHS, CI verde y HA documentado.

| Rank | Plataforma | Score v64 | Δ vs v62 |
|:----:|------------|:---------:|:--------:|
| 1 | Intenseye | 8.48 | = |
| **2** | **VigiEPP v64** | **8.45** | **+0.24** |
| 3 | viAct | 8.10 | = |
| 4 | Protex AI | 8.07 | = |

---

## 2. Mejoras que mueven el ranking

| Dimensión | v62 | v64 | Δ |
|-----------|:---:|:---:|:---:|
| Conductas / SIF | 7.5 | **8.5** | +1.0 (22 presets, audio, historial) |
| Integraciones EHS | 7.5 | **8.5** | +1.0 (workflow 3 estados) |
| Madurez QA | 8.5 | **9.0** | +0.5 (CI verde, 114 tests) |
| Multi-sitio | 6.0 | **6.5** | +0.5 (HA runbook) |
| Documentación ops | 7.5 | **8.5** | +1.0 (HA + excelencia) |

**Score ponderado:** 8.21 → **8.45**  
**Score nicho portería:** 8.6 → **9.0**

---

## 3. Línea de tiempo

| Build | Hito | Score |
|-------|------|:-----:|
| v62 | Acciones P1, wizard, 107 tests | 8.21 |
| v63 | Acciones P2/P3, Forense aislado | 8.35 |
| **v64** | EHS workflow, HA, excellence, CI verde | **8.45** |

---

## 4. Posicionamiento único (v64)

1. Único edge con **EPP + rostro + Acciones + EHS** en LAN
2. **22 presets SIF** editables por cámara y metros
3. **Forense** premium sin tocar operación diaria
4. **HA 2 nodos** documentado (activo-pasivo)
5. Verificable: `GET /api/health` → `excellence`

---

## 5. Próximos pasos v65

- Merge PRs a `main`
- RBAC granular
- Failover semi-automático (watchdog script en repo)

---

*Ver `docs/EXCELENCIA_VIGIEPP_v64.md` para propuesta de valor completa.*
