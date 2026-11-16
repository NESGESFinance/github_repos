"""Fábrica de la aplicación FastAPI de NGFS."""

from __future__ import annotations

from fastapi import FastAPI

from ngfs import __version__
from ngfs.api import rutas_auth, rutas_expedientes, rutas_sistema
from ngfs.config import Configuracion, obtener_configuracion
from ngfs.db import BaseDeDatos
from ngfs.uasi_adaptador import AdaptadorUASI

DESCRIPCION = (
    "NGFSistem (NGFS) — capa de gestión, trazabilidad y auditoría del ecosistema NESGESFinance. "
    "Prototipo v0.1: expedientes con máquina de estados de 8 etapas, RBAC, decisiones con supervisión "
    "humana obligatoria, bitácora encadenada SHA-256 y adaptador UASI v5 opcional y consultivo."
)


def crear_app(cfg: Configuracion | None = None, uasi: AdaptadorUASI | None = None) -> FastAPI:
    cfg = cfg or obtener_configuracion()
    app = FastAPI(title="NGFSistem (NGFS)", version=__version__, description=DESCRIPCION)
    app.state.cfg = cfg
    app.state.db = BaseDeDatos(cfg.database_url)
    app.state.db.crear_tablas()
    app.state.uasi = uasi or AdaptadorUASI(cfg)
    app.include_router(rutas_sistema.router)
    app.include_router(rutas_auth.router)
    app.include_router(rutas_expedientes.router)
    return app
