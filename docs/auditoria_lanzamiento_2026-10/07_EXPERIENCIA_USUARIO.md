# 07 — Experiencia de usuario y accesibilidad

## Prueba manual (browser real)

Agente computer-use + artefactos `/opt/cursor/artifacts/`:

- Login PIN, wizard día cero, 8 módulos navegados sin error fatal.
- Responsive **390×844**: layout usable (`10-responsive-mode-390x844.webp`).

## Coherencia visual

- Design system oscuro, tipografía Barlow/Source Sans (Google Fonts — CSP corregido v68).
- Roles: badge portería visible; admin sin badge.

## Accesibilidad (revisión código + UI limitada)

| Criterio WCAG 2.2 AA | Observación |
|----------------------|-------------|
| Contraste | Tema oscuro con acento naranja; **no** medido con contrast checker |
| Teclado | Tabs con `role="tablist"`; wizard modal — foco no auditado exhaustivamente |
| Semántica | Labels en formularios auth; video/canvas con alternativas parciales |
| Lectores de pantalla | **No verificado** con NVDA/VoiceOver |

## Issues UX

| ID | Sev | Detalle |
|----|-----|---------|
| AUD-VIG-002 | MED | CSP fonts (corregido) |
| AUD-VIG-012 | LOW | Logout en topbar puede requerir scroll horizontal |
| AUD-VIG-040 | INFO | Wizard 8 pasos puede interrumpir operador experiente — tiene «Configurar después» |

## Conclusión UX

**Funcional y coherente** para operador faena; **conformidad WCAG AA no certificada** (falta auditoría automatizada).
