"""Bitácora de auditoría encadenada por hash SHA-256.

Cada evento contiene ``hash_anterior`` (hash del evento previo; el primero usa
``GENESIS``) y ``hash`` = SHA-256 del JSON canónico de sus campos. Cualquier
alteración de un evento, o de su orden, rompe la cadena y es detectada por
``verificar_cadena``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ngfs.modelos import EventoAuditoria, Usuario

GENESIS = "0" * 64


def json_canonico(datos: Any) -> str:
    return json.dumps(datos, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def calcular_hash(campos: dict[str, Any]) -> str:
    return hashlib.sha256(json_canonico(campos).encode("utf-8")).hexdigest()


def _campos(ev: EventoAuditoria) -> dict[str, Any]:
    return {
        "secuencia": ev.secuencia,
        "marca_tiempo": ev.marca_tiempo,
        "actor_id": ev.actor_id,
        "actor": ev.actor,
        "accion": ev.accion,
        "entidad_tipo": ev.entidad_tipo,
        "entidad_id": ev.entidad_id,
        "datos": ev.datos,
        "hash_anterior": ev.hash_anterior,
    }


def registrar_evento(
    sesion: Session,
    *,
    actor: Usuario | None,
    accion: str,
    entidad_tipo: str,
    entidad_id: str | int,
    datos: dict[str, Any] | None = None,
) -> EventoAuditoria:
    """Añade un evento a la cadena. Se confirma junto con la transacción del llamador."""
    ultimo = sesion.execute(
        select(EventoAuditoria).order_by(EventoAuditoria.secuencia.desc()).limit(1)
    ).scalar_one_or_none()
    ev = EventoAuditoria(
        secuencia=(ultimo.secuencia + 1) if ultimo else 1,
        marca_tiempo=datetime.now(UTC).isoformat(),
        actor_id=actor.id if actor else None,
        actor=actor.usuario if actor else "sistema",
        accion=accion,
        entidad_tipo=entidad_tipo,
        entidad_id=str(entidad_id),
        datos=json_canonico(datos or {}),
        hash_anterior=ultimo.hash if ultimo else GENESIS,
    )
    ev.hash = calcular_hash(_campos(ev))
    sesion.add(ev)
    sesion.flush()
    return ev


@dataclass
class ResultadoVerificacion:
    integra: bool
    eventos_verificados: int
    primer_error_secuencia: int | None = None
    detalle: str = "Cadena íntegra."


def verificar_cadena(sesion: Session) -> ResultadoVerificacion:
    anterior = GENESIS
    esperado = 1
    n = 0
    for ev in sesion.execute(select(EventoAuditoria).order_by(EventoAuditoria.secuencia)).scalars():
        if ev.secuencia != esperado:
            return ResultadoVerificacion(False, n, ev.secuencia, f"Secuencia discontinua: se esperaba {esperado}.")
        if ev.hash_anterior != anterior:
            return ResultadoVerificacion(False, n, ev.secuencia, "hash_anterior no coincide con el evento previo.")
        if calcular_hash(_campos(ev)) != ev.hash:
            return ResultadoVerificacion(False, n, ev.secuencia, "El contenido del evento fue alterado (hash no coincide).")
        anterior = ev.hash
        esperado += 1
        n += 1
    return ResultadoVerificacion(True, n)


def contar_eventos(sesion: Session) -> int:
    return int(sesion.execute(select(func.count(EventoAuditoria.id))).scalar_one())
