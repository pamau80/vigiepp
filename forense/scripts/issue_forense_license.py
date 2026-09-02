#!/usr/bin/env python3
"""Emite licencia Forense firmada para despliegue edge.

Ejemplo:
  PYTHONPATH=backend:forense python forense/scripts/issue_forense_license.py \\
    --site faena-norte --years 1

Requiere VIGIEPP_FORENSE_SIGNING_KEY en producción (no usar la clave dev).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import UTC, datetime

# Permite ejecutar sin instalar paquete
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from forense.app.license import parse_license_key, sign_license, verify_license  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Emitir licencia VigiEPP Forense edge")
    parser.add_argument("--site", required=True, help="Identificador de faena (ej. faena-norte)")
    parser.add_argument("--years", type=float, default=1.0, help="Vigencia en años desde hoy")
    parser.add_argument("--days", type=int, default=0, help="Días adicionales de vigencia")
    parser.add_argument("--unix-exp", type=int, default=0, help="Expiración Unix exacta (opcional)")
    parser.add_argument("--verify", action="store_true", help="Verificar licencia generada")
    args = parser.parse_args()

    if args.unix_exp > 0:
        exp = args.unix_exp
    else:
        exp = int(time.time() + int(args.years * 365.25 * 86400) + args.days * 86400)

    try:
        license_key = sign_license(args.site, exp)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    exp_dt = datetime.fromtimestamp(exp, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    print("=== Licencia VigiEPP Forense ===")
    print(f"Sitio:      {args.site}")
    print(f"Expira:     {exp_dt} (unix {exp})")
    print(f"Licencia:   {license_key}")
    print()
    print("Agregar al .env del servidor edge:")
    print(f"VIGIEPP_FORENSE=1")
    print(f"VIGIEPP_FORENSE_LICENSE={license_key}")

    if args.verify:
        os.environ.setdefault("VIGIEPP_FORENSE", "1")
        ok, detail = verify_license(license_key)
        parsed = parse_license_key(license_key)
        print()
        print(f"Verificación: {'OK' if ok else 'FALLÓ'} — {detail}")
        print(f"Parse: {parsed}")


if __name__ == "__main__":
    main()
