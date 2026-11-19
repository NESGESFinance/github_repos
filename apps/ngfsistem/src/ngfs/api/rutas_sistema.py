"""Auditoría, salud y metadatos (máquina de estados y matriz RBAC)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from ngfs import __version__, rbac
from ngfs.api.dependencias import SesionDep, UsuarioDep, exigir_global
from ngfs.auditoria import verificar_cadena
from ngfs.esquemas import EventoSalida, VerificacionCadena
from ngfs.estados import ETAPAS, TRANSICIONES, diagrama_mermaid
from ngfs.modelos import EventoAuditoria

router = APIRouter()


@router.get("/salud", tags=["sistema"])
def salud(request: Request) -> dict[str, Any]:
    return {"estado": "ok", "servicio": "NGFSistem", "version": __version__,
            "uasi_habilitado": request.app.state.uasi.habilitado}


@router.get("/auditoria", response_model=list[EventoSalida], tags=["auditoría"])
def listar_eventos(usuario: UsuarioDep, sesion: SesionDep, desde_secuencia: int = Query(1, ge=1),
                   limite: int = Query(100, ge=1, le=1000)) -> list[EventoAuditoria]:
    exigir_global(usuario, rbac.VER_AUDITORIA)
    consulta = (select(EventoAuditoria).where(EventoAuditoria.secuencia >= desde_secuencia)
                .order_by(EventoAuditoria.secuencia).limit(limite))
    return list(sesion.execute(consulta).scalars())


@router.get("/auditoria/verificar", response_model=VerificacionCadena, tags=["auditoría"])
def verificar(usuario: UsuarioDep, sesion: SesionDep) -> VerificacionCadena:
    exigir_global(usuario, rbac.VERIFICAR_AUDITORIA)
    r = verificar_cadena(sesion)
    return VerificacionCadena(integra=r.integra, eventos_verificados=r.eventos_verificados,
                              primer_error_secuencia=r.primer_error_secuencia, detalle=r.detalle)


@router.get("/meta/estados", tags=["sistema"])
def meta_estados(_usuario: UsuarioDep) -> dict[str, Any]:
    return {
        "etapas": [{"estado": e.value, "etapa": n, "nombre": nombre} for e, (n, nombre) in ETAPAS.items()],
        "transiciones": [{"accion": t.accion, "desde": t.desde.value, "hacia": t.hacia.value,
                          "roles": sorted(r.value for r in t.roles), "decision_humana": t.decision_humana,
                          "requiere_justificacion": t.requiere_justificacion} for t in TRANSICIONES],
        "mermaid": diagrama_mermaid(),
    }


@router.get("/meta/rbac", tags=["sistema"])
def meta_rbac(_usuario: UsuarioDep) -> dict[str, Any]:
    return {
        "matriz": {r.value: {e.value: sorted(a) for e, a in fila.items()} for r, fila in rbac.MATRIZ.items()},
        "acciones_globales": {a: sorted(r.value for r in roles) for a, roles in rbac.ACCIONES_GLOBALES.items()},
    }
