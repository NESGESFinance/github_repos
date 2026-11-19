"""Punto de entrada ASGI: ``uvicorn ngfs.main:app``."""

from ngfs.app import crear_app

app = crear_app()
