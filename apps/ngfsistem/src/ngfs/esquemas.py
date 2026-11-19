"""Esquemas Pydantic de entrada/salida de la API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ngfs.estados import Rol


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - tipo de token OAuth2, no es un secreto
    expira_en_minutos: int


class UsuarioCrear(BaseModel):
    usuario: str = Field(pattern=r"^[A-Za-z0-9_.@\-]{3,64}$")
    nombre: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=128)
    rol: Rol


class UsuarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario: str
    nombre: str
    rol: str
    activo: bool


class ExpedienteCrear(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(default="", max_length=10_000)
    monto_solicitado: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=2)
    moneda: str = Field(default="USD", pattern=r"^[A-Z]{3,8}$")


class ExpedienteEditar(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=10_000)
    monto_solicitado: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=2)
    moneda: str | None = Field(default=None, pattern=r"^[A-Z]{3,8}$")


class ExpedienteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    titulo: str
    descripcion: str
    monto_solicitado: Decimal | None
    moneda: str
    estado: str
    etapa: int
    etapa_nombre: str
    solicitante_id: int
    creado_en: datetime
    actualizado_en: datetime


class SolicitudTransicion(BaseModel):
    accion: str = Field(min_length=1, max_length=64)
    justificacion: str = Field(default="", max_length=5_000)
    confirmacion_humana: bool = Field(
        default=False,
        description="Obligatorio en transiciones de decisión: confirma que una persona revisó y decide.",
    )


class TransicionDisponible(BaseModel):
    accion: str
    hacia: str
    decision_humana: bool
    requiere_justificacion: bool
    descripcion: str


class HistorialSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    accion: str
    desde: str
    hacia: str
    actor_id: int
    justificacion: str
    decision_humana: bool
    creado_en: datetime


class DocumentoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    expediente_id: int
    nombre: str
    tipo_mime: str
    tamano_bytes: int
    sha256: str
    subido_por_id: int
    etapa: str
    creado_en: datetime


class VerificacionDocumento(BaseModel):
    documento_id: int
    coincide: bool
    sha256_registrado: str
    sha256_recibido: str


class EventoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    secuencia: int
    marca_tiempo: str
    actor_id: int | None
    actor: str
    accion: str
    entidad_tipo: str
    entidad_id: str
    datos: str
    hash_anterior: str
    hash: str


class VerificacionCadena(BaseModel):
    integra: bool
    eventos_verificados: int
    primer_error_secuencia: int | None
    detalle: str


class AnalisisSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    expediente_id: int
    solicitado_por_id: int
    disponible: bool
    resultado: dict[str, Any]
    creado_en: datetime
