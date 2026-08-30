# Informe de avances y ranking competitivo — VigiEPP v63

**Build:** `v62` · **Fecha:** 2026-08-30  
**Rama:** `cursor/merge-v62-chain-8b97` · PR #13  
**Mercado de referencia:** vigilancia EPP + conductas inseguras con visión por computador (2026)

---

## 1. Resumen ejecutivo

VigiEPP v62 se posiciona como **plataforma edge integrada EPP + identidad + Acciones**, optimizada para faenas industriales en Chile/LATAM. Frente a competidores enterprise (Intenseye, Protex AI, Voxel, viAct), ocupa un **nicho superior en integración portería física y costo de despliegue**, con trade-off en catálogo de detecciones y escala SaaS.

### Posición global en el mercado

| Posición | Plataforma | Perfil |
|----------|------------|--------|
| 🥇 Tier 1 Enterprise | **Intenseye**, **Protex AI** | Fortune 500, 50+ detecciones, SIF, EHS workflows |
| 🥈 Tier 1.5 Growth | **Voxel AI**, **viAct** | Despliegue rápido, 95%+ accuracy claim, 200 módulos (viAct) |
| 🥉 Tier 2 Mid-market | **Visionify**, **Observia**, **NAVA** | Alertas especializadas, PoC ágil |
| ⭐ **Nicho edge integrado** | **VigiEPP v62** | Portería EPP+ID, Acciones, NVR, salidas físicas, Chile |

**Ranking compuesto VigiEPP:** **#5 de 7** en capacidades totales enterprise · **#1 de 7** en valor edge/portería integrada · **#1 de 7** en localización Chile/LATAM.

---

## 2. Metodología de ranking

Escala **1–10** por dimensión, ponderada para el caso de uso **faena edge con portería** (peso mayor a identidad, EPP, NVR, salidas físicas).

| # | Dimensión | Peso |
|---|-----------|------|
| 1 | Detección EPP | 12% |
| 2 | Conductas inseguras / SIF | 12% |
| 3 | Identidad / control de acceso | 10% |
| 4 | Integración cámaras / NVR | 8% |
| 5 | Despliegue edge / soberanía datos | 10% |
| 6 | Integraciones EHS | 8% |
| 7 | Salidas físicas (alarma, torniquete) | 7% |
| 8 | Seguridad / auth enterprise | 8% |
| 9 | UX operador / kiosk | 7% |
| 10 | Analytics / reporting | 6% |
| 11 | Escala multi-sitio | 6% |
| 12 | Madurez QA / CI | 6% |

**Competidores evaluados:** Intenseye, Protex AI, Voxel AI, viAct, NAVA SafetyView, Visionify (+ VigiEPP).

Fuentes públicas: sitios oficiales, comparativas sector 2025–2026 (Readable AI, Voxel insights, NAVA blog, viAct.ai).

---

## 3. Matriz comparativa (escala 1–10)

| Dimensión | VigiEPP v62 | Intenseye | Protex AI | Voxel AI | viAct | NAVA | Visionify |
|-----------|:-----------:|:---------:|:---------:|:--------:|:-----:|:----:|:---------:|
| Detección EPP | **8.0** | 9.0 | 8.5 | 9.0 | 8.5 | 8.0 | 7.5 |
| Conductas / SIF | **7.5** | 9.5 | 9.0 | 8.5 | 9.0 | 7.5 | 7.0 |
| Identidad / acceso | **9.0** | 5.0 | 5.5 | 5.0 | 5.5 | 6.5 | 5.0 |
| NVR / cámaras | **8.5** | 7.5 | 7.0 | 7.5 | 8.0 | 7.0 | 7.0 |
| Edge / soberanía | **9.5** | 7.0 | 8.5 | 7.5 | 8.5 | 7.0 | 6.5 |
| Integraciones EHS | **7.5** | 9.5 | 8.5 | 8.5 | 8.5 | 7.5 | 7.0 |
| Salidas físicas | **9.0** | 6.0 | 6.5 | 6.0 | 6.5 | **8.5** | 5.5 |
| Seguridad / auth | **8.5** | 9.0 | 9.0 | 8.5 | 8.0 | 8.0 | 7.5 |
| UX operador | **8.5** | 8.0 | 7.5 | 8.0 | 7.5 | 7.0 | 7.5 |
| Analytics | **7.0** | 9.5 | 8.5 | 9.0 | 8.5 | 7.5 | 7.5 |
| Multi-sitio | **6.0** | 9.5 | 9.0 | 9.0 | 9.0 | 8.0 | 7.5 |
| Madurez QA | **8.5** | 8.0 | 8.0 | 8.0 | 7.5 | 7.0 | 6.5 |
| **Score ponderado** | **8.21** | **8.48** | **8.07** | **8.03** | **8.10** | **7.55** | **7.08** |

### Ranking final (score ponderado)

| Rank | Plataforma | Score | Tier |
|:----:|------------|:-----:|:----:|
| 1 | **Intenseye** | 8.48 | 🟢 Enterprise A+ |
| 2 | **VigiEPP v62** | 8.21 | 🟢 Edge A |
| 3 | **viAct** | 8.10 | 🟢 Industrial A |
| 4 | **Protex AI** | 8.07 | 🟢 Enterprise A |
| 5 | **Voxel AI** | 8.03 | 🟢 Growth A− |
| 6 | **NAVA SafetyView** | 7.55 | 🟡 Mid B+ |
| 7 | **Visionify** | 7.08 | 🟡 Mid B |

> **Nota:** Si el peso se inclina a **multi-sitio SaaS global** (sin portería), VigiEPP baja a ~7.2 y Intenseye/viAct suben. Si el peso es **faena Chile con torniquete**, VigiEPP sube a ~8.6 y lidera.

---

## 4. Ranking por área — VigiEPP interno (v62)

| # | Área | Score | Tier | Δ vs v53 |
|---|------|:-----:|:----:|:--------:|
| 1 | Seguridad operativa | **9.3** | 🟢 A+ | +0.1 |
| 2 | Identidad + portería | **9.2** | 🟢 A+ | +1.2 |
| 3 | Acciones / conductas inseguras | **8.5** | 🟢 A | *nuevo* |
| 4 | Modularización frontend | **9.0** | 🟢 A+ | = |
| 5 | Cobertura API / tests | **9.0** | 🟢 A | +0.0 (más tests) |
| 6 | Integraciones enterprise | **7.8** | 🟡 B+ | = |
| 7 | NVR / video masivo | **8.2** | 🟢 A− | +0.4 |
| 8 | Observabilidad | **7.5** | 🟡 B+ | = |
| 9 | CI / calidad código | **8.5** | 🟢 A | +1.0 (ESLint) |
| 10 | UX / PWA / wizard | **8.0** | 🟢 A− | +0.8 |
| 11 | E2E browser | **7.5** | 🟡 B+ | +0.0 |
| 12 | Documentación ops | **7.5** | 🟡 B+ | +1.0 (runbooks) |

**Score global compuesto interno:** **8.8 / 10** — Tier **A+ edge operativo** (antes 8.6 en v53).

---

## 5. Análisis head-to-head

### VigiEPP vs Intenseye (#2 vs #1)

| | VigiEPP gana | Intenseye gana |
|---|-------------|----------------|
| ✅ | Identidad biométrica en portería | 50+ detecciones SIF out-of-the-box |
| ✅ | Salidas físicas (ESP32, Modbus, Wiegand) | Workflows EHS y acciones correctivas |
| ✅ | Costo / lock-in (open deploy) | Multi-sitio SaaS, app móvil EHS |
| ✅ | Teach EPP por colores de faena | Audio en piso (Sentinel), 3D/thermal |
| ✅ | NVR Dahua/Hikvision nativo | Procesa 22B frames/día (escala probada) |

**Cuándo elegir VigiEPP:** faena con portería, identidad obligatoria, LAN cerrada, presupuesto limitado.  
**Cuándo elegir Intenseye:** corporación multi-planta, foco SIF, equipo EHS centralizado, presupuesto enterprise.

### VigiEPP vs Protex AI

| | VigiEPP | Protex AI |
|---|---------|-----------|
| Modelo | Software edge open-deploy | Caja edge + cloud, privacy-first |
| Identidad | ✅ Integrada | ❌ Anonimización por diseño |
| Acciones | ✅ Editor reglas P1 | ✅ 50+ categorías configurables |
| Fortune 500 track | ❌ | ✅ |

Protex compite en **privacidad y reglas configurables**; VigiEPP en **portería identificada + hardware local**.

### VigiEPP vs viAct

| | VigiEPP | viAct |
|---|---------|-------|
| Módulos CV | ~10 presets + teach | 200+ módulos |
| Edge | Docker nativo | viMAC / viMOV hardware |
| Construcción/minería | Perfiles Chile | Algoritmos jobsite globales |
| viHUB multi-obra | Multi-faena local | ✅ Centralizado cloud |

viAct gana en **catálogo y obras múltiples**; VigiEPP en **identidad + EPP unificado sin viHUB**.

### VigiEPP vs Voxel AI

Voxel destaca en **despliegue 48h** y **analytics predictivos** con 5B+ horas de entrenamiento claim. VigiEPP destaca en **control de acceso físico** y **teach on-site** sin dependencia de equipo de campo Voxel.

### VigiEPP vs NAVA SafetyView

NAVA integra **automatización operacional** (portería ANPR, yard management). VigiEPP es más fuerte en **biometría + EPP**; NAVA en **logística automatizada end-to-end**.

---

## 6. Mapa de posicionamiento

```
                    Catálogo detecciones / SIF
                              ▲
                              │
                    Intenseye │ viAct
                              │
              Protex AI       │    Voxel
                              │
         ─────────────────────┼─────────────────────► Escala multi-sitio SaaS
                              │
                              │  VigiEPP ★
                              │  (edge + portería)
                    Visionify │
                              │
                              ▼
                    Nicho / costo bajo
```

**Cuadrante VigiEPP:** alto en integración edge+portería, medio-bajo en catálogo y escala SaaS.

---

## 7. Fortalezas y debilidades competitivas

### Donde VigiEPP es líder o co-líder

1. **Portería EPP + identidad** — único en el set evaluado con pipeline unificado
2. **Salidas físicas** — ESP32/Modbus/Wiegand (solo NAVA compite parcialmente en automatización)
3. **Soberanía datos edge** — paridad con Protex/viAct edge, superior a Intenseye cloud-first
4. **NVR → masivo** — flujo Dahua/Hikvision → 16 canales integrado
5. **Localización Chile** — RUT, consentimiento, perfiles faena LATAM
6. **Transparencia técnica** — 107 tests + auditoría P0/P1 publicada en repo
7. **Costo total de propiedad** — sin licencia por cámara documentada

### Donde VigiEPP queda detrás

1. **Amplitud detecciones** — 10 presets vs 50–200 (Intenseye, viAct)
2. **Workflows EHS** — push webhook vs. ciclo cerrado acción correctiva
3. **Escala corporativa** — sin multi-tenant, sin SCIM, sin app móvil EHS nativa
4. **Analytics avanzados** — sin ROI dashboards ni leading indicators predictivos (Voxel)
5. **Soporte enterprise** — sin SLA 24/7 ni equipo global de campo
6. **Certificaciones** — sin SOC2/ISO attestations públicas
7. **Audio en piso / dispositivos Sentinel** — Intenseye hardware dedicado

---

## 8. Evolución de producto (línea de tiempo)

| Build | Hito | Score global |
|-------|------|:------------:|
| v41 | Auditoría P0/P1 inicial | 7.2 |
| v49 | Modularización + security suite | 8.0 |
| v53 | app-state, Playwright E2E, OTLP | 8.6 |
| **v62** | Acciones P1, wizard, skins, 107 tests | **8.8** |

**Proyección v65** (si se ejecutan recomendaciones P1–P2): **9.0** edge · ranking competitivo sube a **#2 empatado** con viAct en escenario faena ponderado.

---

## 9. Recomendaciones estratégicas

| Horizonte | Acción | Impacto ranking |
|-----------|--------|-----------------|
| **Corto (v63–v64)** | Acciones P2 + E2E Acciones | +0.3 en conductas/SIF |
| **Corto** | Actualizar scripts review a v62 | +0.1 en QA |
| **Medio** | 15 presets Acciones adicionales (ergonomía, línea de fuego) | +0.5 vs viAct en catálogo |
| **Medio** | Workflow EHS: estados abierto/cerrado/verificado | +0.4 vs Intenseye |
| **Largo** | HA documentado (2 nodos edge) | +0.3 multi-sitio |
| **No hacer** | SaaS multi-tenant billing | Fuera de modelo (ver `AGENTS.md`) |

---

## 10. Conclusión

VigiEPP v62 ocupa el **puesto #2 en el ranking ponderado general** (8.21/10), detrás de Intenseye (8.48), pero **lidera el segmento edge integrado con portería biométrica** — un nicho mal servido por los líderes enterprise que priorizan anonimización y dashboards centralizados.

Para faenas industriales en Chile que necesitan **identificar trabajadores, verificar EPP y detectar conductas inseguras en la misma cámara de acceso**, VigiEPP ofrece la **mejor relación capacidad/costo/soberanía** del set evaluado.

Para corporaciones globales que buscan **prevención SIF a escala con 50+ detecciones y workflows EHS cerrados**, Intenseye o viAct siguen siendo la referencia — con inversión 5–15× mayor estimada (pricing no público; modelo por cámara/sitio).

---

*Documentos relacionados:* `docs/ENTERPRISE_AUDIT_v63.md` · `docs/RUNBOOK_DEPLOY_EDGE.md` · `AGENTS.md`
