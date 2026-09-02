# Licencia VigiEPP Forense — despliegue edge

Forense requiere licencia activa en producción (`VIGIEPP_FORENSE=1`).

## Desarrollo / pruebas

```env
VIGIEPP_FORENSE=1
VIGIEPP_FORENSE_LICENSE=dev
```

## Producción (faena)

### 1. Clave de firma (solo en servidor emisor, no en el edge)

```bash
export VIGIEPP_FORENSE_SIGNING_KEY="$(openssl rand -hex 32)"
# Guardar en gestor de secretos — NUNCA commitear
```

### 2. Emitir licencia por sitio

```bash
PYTHONPATH=backend:forense python forense/scripts/issue_forense_license.py \
  --site faena-norte --years 1 --verify
```

Salida ejemplo:

```
VIGIEPP_FORENSE_LICENSE=faena-norte.1785600000.a1b2c3d4e5f6...
```

### 3. Configurar en el servidor edge

```env
VIGIEPP_FORENSE=1
VIGIEPP_FORENSE_LICENSE=faena-norte.1785600000.a1b2c3d4e5f6...
# NO incluir VIGIEPP_FORENSE_SIGNING_KEY en el edge (solo quien emite licencias)
```

### 4. Verificar

```bash
curl -s http://127.0.0.1:8001/api/forense/health | jq '.license'
# esperado: valid: true, detail: "licencia faena-norte"
```

## Formato

`site_id.unix_expiracion.firma_hmac_sha256_32hex`

- **site_id:** identificador de faena (sin puntos)
- **unix_exp:** timestamp UTC de expiración
- **firma:** HMAC-SHA256 truncado a 32 hex del payload `site_id.unix_exp`

## Renovación

Antes de expirar, emitir nueva licencia con el mismo `site_id` y fecha extendida. Actualizar `.env` y reiniciar Forense (`forense/start.sh` o contenedor).

## Seguridad

| Variable | Edge faena | Emisor licencias |
|----------|------------|------------------|
| `VIGIEPP_FORENSE_LICENSE` | Sí | No |
| `VIGIEPP_FORENSE_SIGNING_KEY` | **No** | Sí |
