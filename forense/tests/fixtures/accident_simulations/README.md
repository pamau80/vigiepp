# Fixtures fotorrealistas — escenarios de accidente

Imágenes de referencia **fotorrealistas** (estilo CCTV / foto de faena) para pruebas de biblioteca y matching en VigiEPP Forense.

## Escenarios

| Archivo | Escenario |
|---------|-----------|
| `01_atropello_camion_peaton.png` | Near-miss atropello camión–peatón |
| `02_caida_desde_altura.png` | Caída desde altura sin arnés |
| `03_caida_mismo_nivel.png` | Resbalón mismo nivel |
| `04_maniobra_temeraria_montacargas.png` | Retroceso montacargas punto ciego |
| `05_proximidad_carga_suspendida.png` | Bajo carga suspendida |
| `06_colision_interseccion_patio.png` | Colisión en cruce de patio |
| `07_atrapamiento_vehiculo_mamparo.png` | Atrapamiento vehículo–mamparo |

## Uso en Forense

1. Biblioteca → **Agregar situación** → subir el PNG correspondiente.
2. Usar título/descripción/tags del `manifest.json`.
3. Ejecutar tests: `pytest forense/tests/test_accident_simulations.py -q`

## Validación

```bash
.venv/bin/python forense/scripts/validate_accident_fixtures.py
```

**Nota:** Son escenas de **near-miss** para entrenamiento/prueba, no footage real de víctimas. Para video real de faena, subir el MP4 en un trabajo forense.
