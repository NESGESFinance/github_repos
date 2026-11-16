"""Fixtures comunes: app con SQLite en memoria y utilidades para crear usuarios y expedientes."""

from __future__ import annotations

import functools
from collections.abc import Iterator
from typing import Any

import bcrypt
import pytest
from fastapi.testclient import TestClient

from ngfs import seguridad
from ngfs.app import crear_app
from ngfs.config import Configuracion
from ngfs.estados import Rol
from ngfs.modelos import Usuario
from ngfs.uasi_adaptador import AdaptadorUASI

PASSWORD = "Clave-Segura-2026!"

# Coste bcrypt reducido solo en pruebas (velocidad); producción usa el valor por defecto de bcrypt.
bcrypt.gensalt = functools.partial(bcrypt.gensalt, rounds=4)


def cfg_pruebas(**extra: Any) -> Configuracion:
    base: dict[str, Any] = {"entorno": "pruebas", "database_url": "sqlite://", "jwt_secreto": "x" * 40, "max_intentos_login": 3}
    base.update(extra)
    return Configuracion(**base)


class Entorno:
    def __init__(self, cfg: Configuracion, uasi: AdaptadorUASI | None = None) -> None:
        self.app = crear_app(cfg, uasi)
        self.cliente = TestClient(self.app)
        self._cabeceras: dict[str, dict[str, str]] = {}

    def sesion(self) -> Any:
        return self.app.state.db.fabrica()

    def usuario(self, nombre: str, rol: Rol) -> Usuario:
        with self.sesion() as s:
            u = Usuario(usuario=nombre, nombre=nombre, password_hash=seguridad.hashear_password(PASSWORD), rol=rol.value)
            s.add(u)
            s.commit()
            return u

    def login(self, nombre: str, password: str = PASSWORD) -> Any:
        return self.cliente.post("/auth/login", data={"username": nombre, "password": password})

    def h(self, nombre: str) -> dict[str, str]:
        if nombre not in self._cabeceras:
            r = self.login(nombre)
            assert r.status_code == 200, r.text
            self._cabeceras[nombre] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return self._cabeceras[nombre]

    def crear_expediente(self, solicitante: str = "sol", titulo: str = "Proyecto agrícola sostenible") -> dict[str, Any]:
        datos = {"titulo": titulo, "monto_solicitado": "15000.50"}
        r = self.cliente.post("/expedientes", json=datos, headers=self.h(solicitante))
        assert r.status_code == 201, r.text
        data: dict[str, Any] = r.json()
        return data

    def transicion(self, exp_id: int, usuario: str, accion: str, justificacion: str = "", confirmacion: bool = False) -> Any:
        return self.cliente.post(
            f"/expedientes/{exp_id}/transiciones",
            json={"accion": accion, "justificacion": justificacion, "confirmacion_humana": confirmacion},
            headers=self.h(usuario),
        )

    def llevar_a_cumplimiento(self, exp_id: int) -> None:
        for usuario, accion in [("sol", "enviar"), ("ana", "iniciar_revision"), ("ana", "aceptar_documentacion"),
                                ("ana", "enviar_a_cumplimiento")]:
            r = self.transicion(exp_id, usuario, accion)
            assert r.status_code == 200, r.text


@pytest.fixture
def env() -> Iterator[Entorno]:
    e = Entorno(cfg_pruebas())
    for nombre, rol in [("sol", Rol.SOLICITANTE), ("sol2", Rol.SOLICITANTE), ("ana", Rol.ANALISTA),
                        ("cum", Rol.CUMPLIMIENTO), ("com", Rol.COMITE), ("aud", Rol.AUDITOR), ("adm", Rol.ADMINISTRADOR)]:
        e.usuario(nombre, rol)
    yield e
