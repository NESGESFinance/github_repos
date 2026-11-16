"""AC-11 a AC-15: bitácora encadenada, documentos por hash y adaptador UASI."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from conftest import Entorno, cfg_pruebas
from ngfs.auditoria import GENESIS
from ngfs.estados import Rol
from ngfs.modelos import BitacoraInmutableError, EventoAuditoria
from ngfs.uasi_adaptador import AdaptadorUASI

JUST = "Justificación suficiente para la decisión."


def test_ac11_eventos_encadenados(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.transicion(exp_id, "sol", "enviar")
    eventos = env.cliente.get("/auditoria", headers=env.h("aud")).json()
    acciones = [e["accion"] for e in eventos]
    assert "expediente_creado" in acciones and "transicion" in acciones and "login" in acciones
    assert eventos[0]["hash_anterior"] == GENESIS
    for previo, actual in zip(eventos, eventos[1:], strict=False):
        assert actual["hash_anterior"] == previo["hash"]
        assert actual["secuencia"] == previo["secuencia"] + 1
    transicion = next(e for e in eventos if e["accion"] == "transicion")
    assert json.loads(transicion["datos"])["hacia"] == "enviado"


def test_ac12_verificacion_detecta_manipulacion(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.transicion(exp_id, "sol", "enviar")
    r = env.cliente.get("/auditoria/verificar", headers=env.h("aud")).json()
    assert r["integra"] is True and r["eventos_verificados"] >= 3
    # Manipulación directa en la base de datos (saltándose el ORM)
    with env.sesion() as s:
        s.execute(text("UPDATE eventos_auditoria SET datos = '{\"hacia\":\"aprobado\"}' WHERE accion = 'transicion'"))
        s.commit()
    r = env.cliente.get("/auditoria/verificar", headers=env.h("aud")).json()
    assert r["integra"] is False and r["primer_error_secuencia"] is not None


def test_ac12_verificacion_detecta_borrado(env: Entorno) -> None:
    env.crear_expediente()
    env.h("aud")
    with env.sesion() as s:
        s.execute(text("DELETE FROM eventos_auditoria WHERE secuencia = 2"))
        s.commit()
    assert env.cliente.get("/auditoria/verificar", headers=env.h("aud")).json()["integra"] is False


def test_ac12_permisos_de_auditoria(env: Entorno) -> None:
    for usuario in ("sol", "ana", "com"):
        assert env.cliente.get("/auditoria", headers=env.h(usuario)).status_code == 403
        assert env.cliente.get("/auditoria/verificar", headers=env.h(usuario)).status_code == 403
    for usuario in ("aud", "cum", "adm"):
        assert env.cliente.get("/auditoria/verificar", headers=env.h(usuario)).status_code == 200


def test_ac13_bitacora_inmutable_via_orm(env: Entorno) -> None:
    env.crear_expediente()
    with env.sesion() as s:
        ev = s.query(EventoAuditoria).first()
        ev.accion = "alterado"
        with pytest.raises(BitacoraInmutableError):
            s.commit()
        s.rollback()
        ev = s.query(EventoAuditoria).first()
        s.delete(ev)
        with pytest.raises(BitacoraInmutableError):
            s.commit()


def test_ac14_documentos_registrados_por_sha256(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    contenido = b"Estudio de factibilidad v1"
    r = env.cliente.post(f"/expedientes/{exp_id}/documentos", files={"archivo": ("estudio.pdf", contenido, "application/pdf")},
                         headers=env.h("sol"))
    assert r.status_code == 201
    doc = r.json()
    assert doc["sha256"] == hashlib.sha256(contenido).hexdigest() and doc["tamano_bytes"] == len(contenido)
    ok = env.cliente.post(f"/documentos/{doc['id']}/verificar", files={"archivo": ("x", contenido)}, headers=env.h("sol")).json()
    assert ok["coincide"] is True
    malo = env.cliente.post(f"/documentos/{doc['id']}/verificar", files={"archivo": ("x", contenido + b"!")},
                            headers=env.h("sol")).json()
    assert malo["coincide"] is False
    eventos = env.cliente.get("/auditoria", headers=env.h("aud")).json()
    assert any(e["accion"] == "documento_registrado" and doc["sha256"] in e["datos"] for e in eventos)
    # tras enviar, el solicitante ya no puede adjuntar (etapa no editable)
    env.transicion(exp_id, "sol", "enviar")
    assert env.cliente.post(f"/expedientes/{exp_id}/documentos", files={"archivo": ("b.txt", b"b")},
                            headers=env.h("sol")).status_code == 403


def test_ac14_limite_de_tamano() -> None:
    e = Entorno(cfg_pruebas(max_tamano_documento_mb=1))
    e.usuario("sol", Rol.SOLICITANTE)
    exp_id = e.crear_expediente()["id"]
    r = e.cliente.post(f"/expedientes/{exp_id}/documentos", files={"archivo": ("g.bin", b"0" * (1024 * 1024 + 1))},
                       headers=e.h("sol"))
    assert r.status_code == 413


def _en_analisis(e: Entorno) -> int:
    exp_id: int = e.crear_expediente()["id"]
    for usuario, accion in [("sol", "enviar"), ("ana", "iniciar_revision"), ("ana", "aceptar_documentacion")]:
        assert e.transicion(exp_id, usuario, accion).status_code == 200
    return exp_id


def _entorno_uasi(transporte: httpx.BaseTransport | None, habilitado: bool = True) -> Entorno:
    cfg = cfg_pruebas(uasi_habilitado=habilitado, uasi_url="http://uasi.invalid")
    e = Entorno(cfg, AdaptadorUASI(cfg, transporte))
    for nombre, rol in [("sol", Rol.SOLICITANTE), ("ana", Rol.ANALISTA), ("aud", Rol.AUDITOR)]:
        e.usuario(nombre, rol)
    return e


def test_ac15_uasi_desactivado_por_defecto(env: Entorno) -> None:
    assert cfg_pruebas().uasi_habilitado is False
    assert env.cliente.get("/salud").json()["uasi_habilitado"] is False
    llamadas: list[httpx.Request] = []

    def registrar(req: httpx.Request) -> httpx.Response:
        llamadas.append(req)
        return httpx.Response(200, json={})

    e = _entorno_uasi(httpx.MockTransport(registrar), habilitado=False)
    exp_id = _en_analisis(e)
    r = e.cliente.post(f"/expedientes/{exp_id}/analisis-uasi", headers=e.h("ana"))
    assert r.status_code == 201 and r.json()["disponible"] is False
    assert llamadas == []


def test_ac15_uasi_consultivo_no_cambia_estado() -> None:
    def responder(req: httpx.Request) -> httpx.Response:
        cuerpo: dict[str, Any] = json.loads(req.content)
        assert cuerpo["origen"] == "NGFS" and "solicitante_id" not in cuerpo["expediente"]
        # UASI "sugiere" aprobar: NGFS debe ignorarlo como decisión
        return httpx.Response(200, json={"riesgo": "bajo", "sugerencia": "aprobar", "nuevo_estado": "aprobado"})

    e = _entorno_uasi(httpx.MockTransport(responder))
    exp_id = _en_analisis(e)
    r = e.cliente.post(f"/expedientes/{exp_id}/analisis-uasi", headers=e.h("ana"))
    assert r.status_code == 201
    res = r.json()["resultado"]
    assert res["disponible"] is True and res["caracter"] == "consultivo" and res["recomendaciones"]["riesgo"] == "bajo"
    assert e.cliente.get(f"/expedientes/{exp_id}", headers=e.h("ana")).json()["estado"] == "en_analisis"
    assert len(e.cliente.get(f"/expedientes/{exp_id}/analisis-uasi", headers=e.h("aud")).json()) == 1


@pytest.mark.parametrize(
    "transporte",
    [
        httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("caído"))),
        httpx.MockTransport(lambda req: httpx.Response(500)),
        httpx.MockTransport(lambda req: httpx.Response(200, content=b"no-json")),
        httpx.MockTransport(lambda req: httpx.Response(200, json=[1, 2])),
    ],
)
def test_ac15_uasi_fallo_no_rompe_ngfs(transporte: httpx.BaseTransport) -> None:
    e = _entorno_uasi(transporte)
    exp_id = _en_analisis(e)
    r = e.cliente.post(f"/expedientes/{exp_id}/analisis-uasi", headers=e.h("ana"))
    assert r.status_code == 201 and r.json()["disponible"] is False
    assert e.cliente.get(f"/expedientes/{exp_id}", headers=e.h("ana")).json()["estado"] == "en_analisis"
    assert e.transicion(exp_id, "ana", "enviar_a_cumplimiento").status_code == 200


def test_ac15_uasi_respeta_rbac() -> None:
    e = _entorno_uasi(httpx.MockTransport(lambda req: httpx.Response(200, json={})))
    exp_id = _en_analisis(e)
    assert e.cliente.post(f"/expedientes/{exp_id}/analisis-uasi", headers=e.h("aud")).status_code == 403
