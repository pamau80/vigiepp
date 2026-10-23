# 08 — Cumplimiento normativo (Chile) — enfoque técnico

**Disclaimer:** esto **no** es asesoría legal. Validación jurídica requiere profesional habilitado.

## Aplicabilidad del producto

VigiEPP procesa **imágenes biométricas / identidad** y evidencia de EPP en faena minera/industrial — probablemente datos personales sensibles.

## Controles técnicos implementados (evidencia código)

| Tema | Implementación |
|------|----------------|
| Minimización | Modo QR-only (`privacy.py`) |
| Retención | Días configurables + job purge |
| Consentimiento | Export CSV consent (`/api/identity/consent.csv`) |
| Seguridad | Auth, RBAC, cifrado secretos, headers |
| Documentación | README privacidad Ley 21.719 en UI Config |

## Ley 19.628 / Ley 21.719

| Obligación | Estado auditoría |
|------------|------------------|
| Política de tratamiento / aviso titulares | **Pendiente legal** — UI no sustituye política escrita |
| Registro de tratamiento | **No verificado** |
| Derechos ARCO/PET | Parcial técnico (export backup); procedimiento operativo **pendiente** |
| Medidas de seguridad | Controles edge documentados en runbook |
| Vigencia Ley 21.719 | Requiere seguimiento normativo 2026+ — **validar con abogado** |

## Consumidor / comercialización B2B

- Producto vendido como **licencia edge**, no suscripción consumo masivo en app.
- Contrato, SLA y condiciones comerciales: **fuera del repositorio**.

## Acciones antes de comercializar

1. Política de privacidad + contrato faena alineados a tratamiento biométrico.
2. DPIA / evaluación impacto (recomendado).
3. Procedimiento respuesta a incidentes y contacto DPD/delegado.
4. Licencia Forense producción (`docs/FORENSE_LICENSE_EDGE.md`).

## Hallazgo

| ID | Sev | Descripción |
|----|-----|-------------|
| AUD-VIG-050 | MED | Controles técnicos sin paquete legal/compliance comercial completo | Decisión negocio + legal |
