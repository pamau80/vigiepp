# VigiEPP Forense

Producto **aislado** de análisis forense de video (informes IA de incidentes).

No modifica VigiEPP principal (`frontend/`, `backend/app/main.py`, pestañas, etc.).

## Arranque

```bash
bash forense/start.sh
```

Abre **http://127.0.0.1:8001/** (VigiEPP sigue en `:8000`).

## Licencia (plan Forense)

```env
VIGIEPP_FORENSE=1
VIGIEPP_FORENSE_LICENSE=dev          # desarrollo
# Producción: clave firmada VIGIEPP_FORENSE_LICENSE=<site>.<exp>.<sig>
```

Solo rol **admin** puede usar Forense (mismo PIN que VigiEPP).

## Datos

Almacenados en `forense/data/` (separado de `backend/data/`).

## Disclaimer

Los informes son **generación IA asistida**. No constituyen peritaje legal ni dictamen oficial.
