"""Autenticación (login JWT) y gestión de usuarios."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select

from ngfs import rbac
from ngfs.api.dependencias import CfgDep, SesionDep, UsuarioDep, como_utc, exigir_global
from ngfs.auditoria import registrar_evento
from ngfs.esquemas import Token, UsuarioCrear, UsuarioSalida
from ngfs.estados import Rol
from ngfs.modelos import Usuario
from ngfs.seguridad import PasswordDebil, emitir_token, hashear_password, validar_password, verificar_password

router = APIRouter()

# Hash ficticio para igualar el tiempo de respuesta cuando el usuario no existe.
_HASH_FICTICIO = hashear_password("ngfs-hash-ficticio-0000")


@router.post("/auth/login", response_model=Token, tags=["autenticación"])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], sesion: SesionDep, cfg: CfgDep) -> Token:
    credenciales_invalidas = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos.", headers={"WWW-Authenticate": "Bearer"}
    )
    usuario = sesion.execute(select(Usuario).where(Usuario.usuario == form.username)).scalar_one_or_none()
    if usuario is None:
        verificar_password(form.password, _HASH_FICTICIO)
        raise credenciales_invalidas
    ahora = datetime.now(UTC)
    bloqueo = como_utc(usuario.bloqueado_hasta)
    if bloqueo and bloqueo > ahora:
        raise HTTPException(status.HTTP_423_LOCKED, "Cuenta bloqueada temporalmente por intentos fallidos.")
    if not usuario.activo or not verificar_password(form.password, usuario.password_hash):
        usuario.intentos_fallidos += 1
        datos: dict[str, object] = {"intentos": usuario.intentos_fallidos}
        if usuario.intentos_fallidos >= cfg.max_intentos_login:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=cfg.minutos_bloqueo)
            usuario.intentos_fallidos = 0
            datos["bloqueado_hasta"] = usuario.bloqueado_hasta.isoformat()
        registrar_evento(sesion, actor=usuario, accion="login_fallido", entidad_tipo="usuario",
                         entidad_id=usuario.id, datos=datos)
        sesion.commit()
        raise credenciales_invalidas
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    registrar_evento(sesion, actor=usuario, accion="login", entidad_tipo="usuario", entidad_id=usuario.id)
    sesion.commit()
    token = emitir_token(cfg, usuario_id=usuario.id, usuario=usuario.usuario, rol=usuario.rol)
    return Token(access_token=token, expira_en_minutos=cfg.jwt_minutos_expiracion)


@router.get("/auth/yo", response_model=UsuarioSalida, tags=["autenticación"])
def yo(usuario: UsuarioDep) -> Usuario:
    return usuario


def crear_usuario(sesion: SesionDep, datos: UsuarioCrear, longitud_minima: int, actor: Usuario | None) -> Usuario:
    """Lógica compartida por la API y el script de administración."""
    try:
        validar_password(datos.password, longitud_minima)
    except PasswordDebil as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if sesion.execute(select(Usuario).where(Usuario.usuario == datos.usuario)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El nombre de usuario ya existe.")
    nuevo = Usuario(usuario=datos.usuario, nombre=datos.nombre, password_hash=hashear_password(datos.password),
                    rol=datos.rol.value)
    sesion.add(nuevo)
    sesion.flush()
    registrar_evento(sesion, actor=actor, accion="usuario_creado", entidad_tipo="usuario", entidad_id=nuevo.id,
                     datos={"usuario": nuevo.usuario, "rol": nuevo.rol})
    sesion.commit()
    return nuevo


@router.post("/usuarios", response_model=UsuarioSalida, status_code=201, tags=["usuarios"])
def alta_usuario(datos: UsuarioCrear, usuario: UsuarioDep, sesion: SesionDep, cfg: CfgDep) -> Usuario:
    exigir_global(usuario, rbac.GESTIONAR_USUARIOS)
    return crear_usuario(sesion, datos, cfg.longitud_minima_password, usuario)


@router.get("/usuarios", response_model=list[UsuarioSalida], tags=["usuarios"])
def listar_usuarios(usuario: UsuarioDep, sesion: SesionDep) -> list[Usuario]:
    exigir_global(usuario, rbac.GESTIONAR_USUARIOS)
    return list(sesion.execute(select(Usuario).order_by(Usuario.id)).scalars())


class UsuarioActualizar(BaseModel):
    rol: Rol | None = None
    activo: bool | None = None


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioSalida, tags=["usuarios"])
def actualizar_usuario(usuario_id: int, datos: UsuarioActualizar, usuario: UsuarioDep, sesion: SesionDep) -> Usuario:
    exigir_global(usuario, rbac.GESTIONAR_USUARIOS)
    objetivo = sesion.get(Usuario, usuario_id)
    if objetivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if objetivo.id == usuario.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un administrador no puede modificar su propio rol o estado.")
    cambios: dict[str, dict[str, object]] = {}
    if datos.rol is not None and datos.rol.value != objetivo.rol:
        cambios["rol"] = {"antes": objetivo.rol, "despues": datos.rol.value}
        objetivo.rol = datos.rol.value
    if datos.activo is not None and datos.activo != objetivo.activo:
        cambios["activo"] = {"antes": objetivo.activo, "despues": datos.activo}
        objetivo.activo = datos.activo
    if cambios:
        registrar_evento(sesion, actor=usuario, accion="usuario_actualizado", entidad_tipo="usuario",
                         entidad_id=objetivo.id, datos=cambios)
    sesion.commit()
    return objetivo
