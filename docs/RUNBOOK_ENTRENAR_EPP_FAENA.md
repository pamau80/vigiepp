# Entrenar EPP de la faena (color y tipo)

El modelo **base** (`SafetyVision YOLOv8s`) reconoce categorías genéricas: casco, chaleco, lentes, guantes.  
**No conoce** el casco blanco de tu contratista, los guantes nitrilo azules ni el chaleco naranja con logo — eso se **entrena en sitio**.

---

## Cuándo entrenar

| Situación | Acción |
|-----------|--------|
| Demo / piloto rápido | Modelo base + perfil **EPP completo faena** |
| Portería en producción | **Entrenar** con fotos reales de la faena |
| Cambio de uniforme / proveedor EPP | Re-entrenar o agregar ejemplos nuevos |

---

## Flujo en la UI (admin)

1. Pestaña **EPP** (Enseñar ropa / EPP).
2. Elegir clase o crear una nueva, por ejemplo:
   - `casco` — subir fotos de **tus** cascos (blanco, naranja, con sticker).
   - `chaleco_fluor` / `polera` / `uniforme_completo` — ropa de la empresa.
   - `lentes` — claros, oscuros, sellados usados en faena.
   - `guantes` — nitrilo, cabritilla, anticorte (manos visibles).
3. **Adjuntar fotos** (30–80 por ítem clave) o **video** de la zona (extrae frames).
4. **Entrenar modelo** (YOLO fine-tune local, ~minutos según CPU/GPU).
5. **Activar modelo** — reemplaza el base en vivo y masivo.

Los datos quedan en `VIGIEPP_DATA_DIR/datasets/custom_ppe/` (no salen del servidor edge).

---

## Dos estrategias válidas

### A) Reutilizar clase base (`casco`, `guantes`, …)

Subís muchas fotos de **tu** EPP bajo la misma clase. El ID sigue siendo `casco` y el perfil **EPP completo** funciona sin cambios.

**Recomendado** para portería estándar.

### B) Clase custom (`casco_blanco_acme`, `guantes_nitrilo_azul`)

Creás prenda nueva con **Nueva prenda**. VigiEPP mapea automáticamente a la familia del perfil (`casco`, `guantes`, etc.) si el nombre contiene esa palabra.

---

## Checklist por ítem

| Ítem | Qué fotografiar | Mínimo orientativo |
|------|-----------------|-------------------|
| **Casco** | Colores y tipos usados, frente y lateral, con y sin barboquejo | 40 fotos |
| **Ropa completa** | Chaleco/flúor, polera y casaca con logo, día y sombra | 50 fotos |
| **Lentes** | Claros, oscuros, sobre rostro, ángulos distintos | 30 fotos |
| **Guantes** | Manos en primer plano, colores y materiales de la faena | 40 fotos |

Incluí ejemplos de **incumplimiento** (`sin_casco`, `sin_chaleco`) si querés alertas más precisas.

---

## Después del entrenamiento

1. Probar en **Vivo** con una persona real en portería.
2. Ajustar perfil **EPP completo faena** (qué ítems son obligatorios).
3. Si guantes/lentes no aparecen: más fotos con **manos/rostro en cuadro** o bajar confianza en Config (solo si hace falta).

---

## Pruebas automáticas

```bash
pytest tests/test_epp_acuity.py -v          # agudeza EPP (modelo base)
python scripts/epp_acuity_report.py         # reporte por ítem
```

Tras entrenar, repetir prueba manual en vivo — el reporte automático usa el modelo **activo**.
