"""Utilidades de línea de comandos.

Crear el administrador inicial (la contraseña se lee de NGFS_ADMIN_PASSWORD o de --password):

    NGFS_ADMIN_PASSWORD='...' python -m ngfs.cli crear-admin --usuario admin --nombre "Administración"
"""

from __future__ import annotations

import argparse
import os
import sys

from fastapi import HTTPException
from pydantic import ValidationError

from ngfs.api.rutas_auth import crear_usuario
from ngfs.config import obtener_configuracion
from ngfs.db import BaseDeDatos
from ngfs.esquemas import UsuarioCrear
from ngfs.estados import Rol


def crear_admin(usuario: str, nombre: str, password: str) -> int:
    cfg = obtener_configuracion()
    db = BaseDeDatos(cfg.database_url)
    db.crear_tablas()
    with db.fabrica() as sesion:
        try:
            nuevo = crear_usuario(sesion, UsuarioCrear(usuario=usuario, nombre=nombre, password=password, rol=Rol.ADMINISTRADOR),
                                  cfg.longitud_minima_password, None)
        except HTTPException as exc:
            print(f"Error: {exc.detail}", file=sys.stderr)
            return 1
        except ValidationError as exc:
            print(f"Error de validación: {exc.errors()[0]['msg']}", file=sys.stderr)
            return 1
    print(f"Administrador '{nuevo.usuario}' creado (id={nuevo.id}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ngfs", description="Herramientas de administración de NGFSistem")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("crear-admin", help="Crea un usuario con rol administrador")
    p.add_argument("--usuario", required=True)
    p.add_argument("--nombre", default="")
    p.add_argument("--password", default=None, help="Preferible usar la variable NGFS_ADMIN_PASSWORD")
    args = parser.parse_args(argv)
    password = args.password or os.environ.get("NGFS_ADMIN_PASSWORD", "")
    if not password:
        print("Error: defina NGFS_ADMIN_PASSWORD o use --password.", file=sys.stderr)
        return 2
    return crear_admin(args.usuario, args.nombre, password)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
