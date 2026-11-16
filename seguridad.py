"""Contraseñas (bcrypt) y tokens de acceso (JWT)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from ngfs.config import Configuracion


class PasswordDebil(ValueError):
    pass


def validar_password(password: str, longitud_minima: int) -> None:
    if len(password) < longitud_minima:
        raise PasswordDebil(f"La contraseña debe tener al menos {longitud_minima} caracteres.")
    if len(password.encode("utf-8")) > 72:
        raise PasswordDebil("La contraseña no puede superar 72 bytes (límite de bcrypt).")
    if password.isalpha() or password.isdigit():
        raise PasswordDebil("La contraseña debe combinar letras y números o símbolos.")


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def emitir_token(cfg: Configuracion, *, usuario_id: int, usuario: str, rol: str) -> str:
    ahora = datetime.now(UTC)
    carga: dict[str, Any] = {
        "sub": str(usuario_id),
        "usr": usuario,
        "rol": rol,
        "tipo": "humano",  # NGFS solo emite tokens a personas; no existen tokens de servicio con permisos de decisión
        "iat": ahora,
        "exp": ahora + timedelta(minutes=cfg.jwt_minutos_expiracion),
    }
    return jwt.encode(carga, cfg.jwt_secreto, algorithm=cfg.jwt_algoritmo)


def decodificar_token(cfg: Configuracion, token: str) -> dict[str, Any]:
    """Lanza ``jwt.PyJWTError`` si el token es inválido o expiró."""
    return jwt.decode(token, cfg.jwt_secreto, algorithms=[cfg.jwt_algoritmo], options={"require": ["exp", "sub"]})
