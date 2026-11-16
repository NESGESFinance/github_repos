"""Modelos ORM de NGFS."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, event
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from ngfs.db import Base


def ahora() -> datetime:
    return datetime.now(UTC)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(32))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Expediente(Base):
    __tablename__ = "expedientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    monto_solicitado: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    moneda: Mapped[str] = mapped_column(String(8), default="USD")
    estado: Mapped[str] = mapped_column(String(32), index=True)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


class HistorialTransicion(Base):
    __tablename__ = "historial_transiciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), index=True)
    accion: Mapped[str] = mapped_column(String(64))
    desde: Mapped[str] = mapped_column(String(32))
    hacia: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    justificacion: Mapped[str] = mapped_column(Text, default="")
    decision_humana: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Documento(Base):
    """Documento adjunto registrado por su huella SHA-256 (el contenido no se almacena)."""

    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    tipo_mime: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    subido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    etapa: Mapped[str] = mapped_column(String(32))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class AnalisisConsultivo(Base):
    """Resultado consultivo del adaptador UASI. Nunca altera el estado del expediente."""

    __tablename__ = "analisis_consultivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), index=True)
    solicitado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    disponible: Mapped[bool] = mapped_column(Boolean)
    resultado: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class EventoAuditoria(Base):
    """Evento de la bitácora encadenada por SHA-256. Solo inserción (append-only)."""

    __tablename__ = "eventos_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    secuencia: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    marca_tiempo: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor: Mapped[str] = mapped_column(String(64))
    accion: Mapped[str] = mapped_column(String(64), index=True)
    entidad_tipo: Mapped[str] = mapped_column(String(32))
    entidad_id: Mapped[str] = mapped_column(String(64))
    datos: Mapped[str] = mapped_column(Text)  # JSON canónico
    hash_anterior: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class BitacoraInmutableError(Exception):
    """Se intentó modificar o borrar un evento de auditoría."""


@event.listens_for(EventoAuditoria, "before_update")
def _bloquear_update(_mapper: Mapper[Any], _conn: Any, _obj: EventoAuditoria) -> None:
    raise BitacoraInmutableError("La bitácora de auditoría es inmutable: no se permiten modificaciones.")


@event.listens_for(EventoAuditoria, "before_delete")
def _bloquear_delete(_mapper: Mapper[Any], _conn: Any, _obj: EventoAuditoria) -> None:
    raise BitacoraInmutableError("La bitácora de auditoría es inmutable: no se permiten borrados.")
