"""Dependencias FastAPI: sesión de BD, configuración, usuario autenticado y control de acceso."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ngfs import rbac
from ngfs.config import Configuracion
from ngfs.estados import Estado, Rol
from ngfs.modelos import Expediente, Usuario
from ngfs.seguridad import decodificar_token
from ngfs.uasi_adaptador import AdaptadorUASI

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def obtener_sesion(request: Request) -> Iterator[Session]:
    yield from request.app.state.db.sesion()


def obtener_cfg(request: Request) -> Configuracion:
    cfg: Configuracion = request.app.state.cfg
    return cfg


def obtener_uasi(request: Request) -> AdaptadorUASI:
    adaptador: AdaptadorUASI = request.app.state.uasi
    return adaptador


SesionDep = Annotated[Session, Depends(obtener_sesion)]
CfgDep = Annotated[Configuracion, Depends(obtener_cfg)]


def _no_autenticado(detalle: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detalle, headers={"WWW-Authenticate": "Bearer"})


def obtener_claims(token: Annotated[str, Depends(oauth2)], cfg: CfgDep) -> dict[str, Any]:
    try:
        return decodificar_token(cfg, token)
    except jwt.ExpiredSignatureError as exc:
        raise _no_autenticado("El token ha expirado.") from exc
    except jwt.PyJWTError as exc:
        raise _no_autenticado("Token inválido.") from exc


ClaimsDep = Annotated[dict[str, Any], Depends(obtener_claims)]


def usuario_actual(claims: ClaimsDep, sesion: SesionDep) -> Usuario:
    try:
        usuario_id = int(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise _no_autenticado("Token inválido.") from exc
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise _no_autenticado("Usuario inexistente o desactivado.")
    if claims.get("rol") != usuario.rol:
        raise _no_autenticado("El rol del usuario cambió; inicie sesión de nuevo.")
    return usuario


UsuarioDep = Annotated[Usuario, Depends(usuario_actual)]


def exigir_global(usuario: Usuario, accion: str) -> None:
    if not rbac.permitido_global(Rol(usuario.rol), accion):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Su rol no permite la acción '{accion}'.")


def cargar_expediente(sesion: Session, usuario: Usuario, expediente_id: int, accion: str = rbac.VER) -> Expediente:
    """Carga un expediente aplicando visibilidad (404) y permiso de acción (403)."""
    exp = sesion.get(Expediente, expediente_id)
    rol = Rol(usuario.rol)
    no_encontrado = HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado.")
    if exp is None:
        raise no_encontrado
    if rol == Rol.SOLICITANTE and exp.solicitante_id != usuario.id:
        raise no_encontrado
    estado = Estado(exp.estado)
    if not rbac.permitido(rol, estado, rbac.VER):
        raise no_encontrado
    if accion != rbac.VER and not rbac.permitido(rol, estado, accion):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"El rol '{rol.value}' no puede ejecutar '{accion}' en la etapa '{estado.value}'.",
        )
    return exp


def como_utc(valor: datetime | None) -> datetime | None:
    """SQLite devuelve fechas sin zona horaria; se normalizan a UTC."""
    if valor is None:
        return None
    return valor if valor.tzinfo else valor.replace(tzinfo=UTC)
