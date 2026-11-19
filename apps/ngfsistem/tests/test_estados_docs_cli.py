"""Definición de la máquina de estados, coherencia con docs/ y script de administración."""

from __future__ import annotations

from pathlib import Path

import pytest

from ngfs import cli, rbac
from ngfs.config import obtener_configuracion
from ngfs.estados import ETAPAS, TRANSICIONES, Estado, diagrama_mermaid

RAIZ = Path(__file__).resolve().parents[1]


def test_ocho_etapas_y_decisiones_humanas() -> None:
    assert sorted({n for n, _ in ETAPAS.values()}) == list(range(1, 9))
    decisiones = {t.accion for t in TRANSICIONES if t.decision_humana}
    assert decisiones == {"aprobar", "rechazar"}
    assert all(t.hacia in (Estado.APROBADO, Estado.RECHAZADO) for t in TRANSICIONES if t.decision_humana)
    assert all(t.requiere_justificacion for t in TRANSICIONES if t.decision_humana)
    # Las únicas vías hacia Aprobado/Rechazado son decisiones humanas
    assert all(t.decision_humana for t in TRANSICIONES if t.hacia in (Estado.APROBADO, Estado.RECHAZADO))


def test_docs_sincronizadas_con_codigo() -> None:
    assert diagrama_mermaid() in (RAIZ / "docs" / "maquina_estados.md").read_text(encoding="utf-8")
    assert rbac.matriz_markdown() in (RAIZ / "docs" / "rbac.md").read_text(encoding="utf-8")


def test_criterios_ac01_a_ac15_documentados() -> None:
    texto = (RAIZ / "docs" / "criterios_aceptacion.md").read_text(encoding="utf-8")
    for i in range(1, 16):
        assert f"AC-{i:02d}" in texto


def test_cli_crear_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("NGFS_ADMIN_PASSWORD", "Admin-Segura-2026!")
    obtener_configuracion.cache_clear()
    try:
        assert cli.main(["crear-admin", "--usuario", "admin"]) == 0
        assert cli.main(["crear-admin", "--usuario", "admin"]) == 1  # duplicado
        monkeypatch.setenv("NGFS_ADMIN_PASSWORD", "debil")
        assert cli.main(["crear-admin", "--usuario", "admin2"]) == 1
        monkeypatch.delenv("NGFS_ADMIN_PASSWORD")
        assert cli.main(["crear-admin", "--usuario", "admin3"]) == 2
    finally:
        obtener_configuracion.cache_clear()
