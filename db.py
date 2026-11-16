"""Motor de base de datos y sesiones SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos."""


def crear_motor(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


class BaseDeDatos:
    """Agrupa motor y fábrica de sesiones para poder inyectarlos (útil en pruebas)."""

    def __init__(self, url: str) -> None:
        self.motor = crear_motor(url)
        self.fabrica = sessionmaker(bind=self.motor, autoflush=False, expire_on_commit=False)

    def crear_tablas(self) -> None:
        from ngfs import modelos  # noqa: F401 - registra los modelos en Base.metadata

        Base.metadata.create_all(self.motor)

    def sesion(self) -> Iterator[Session]:
        with self.fabrica() as s:
            yield s
