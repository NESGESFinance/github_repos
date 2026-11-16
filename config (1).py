"""Configuración de NGFS leída desde variables de entorno (prefijo ``NGFS_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETO_DESARROLLO = "solo-desarrollo-cambiar-este-secreto-ngfs"  # noqa: S105 - valor de desarrollo, rechazado en producción


class Configuracion(BaseSettings):
    """Parámetros de ejecución. Ver ``.env.example`` para la lista completa."""

    model_config = SettingsConfigDict(env_prefix="NGFS_", env_file=".env", extra="ignore", populate_by_name=True)

    entorno: str = Field(default="desarrollo", description="desarrollo | pruebas | produccion")
    database_url: str = Field(default="sqlite:///./ngfs.db", validation_alias="DATABASE_URL")

    jwt_secreto: str = SECRETO_DESARROLLO
    jwt_algoritmo: str = "HS256"
    jwt_minutos_expiracion: int = Field(default=60, ge=1, le=1440)

    max_intentos_login: int = Field(default=5, ge=1)
    minutos_bloqueo: int = Field(default=15, ge=1)
    longitud_minima_password: int = Field(default=12, ge=8)
    max_tamano_documento_mb: int = Field(default=25, ge=1)

    # Adaptador UASI v5 (opcional, aislado, consultivo). Desactivado por defecto.
    uasi_habilitado: bool = False
    uasi_url: str = "http://localhost:8000"
    uasi_ruta_analisis: str = "/api/v5/ngfs/analisis-consultivo"
    uasi_token: str = ""
    uasi_timeout_segundos: float = Field(default=5.0, gt=0, le=60)

    @model_validator(mode="after")
    def _validar_produccion(self) -> Configuracion:
        if self.entorno == "produccion" and (self.jwt_secreto == SECRETO_DESARROLLO or len(self.jwt_secreto) < 32):
            raise ValueError("En producción NGFS_JWT_SECRETO debe definirse con al menos 32 caracteres aleatorios.")
        return self


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
