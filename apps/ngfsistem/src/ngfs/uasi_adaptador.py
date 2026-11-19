"""Adaptador OPCIONAL y aislado hacia UASI v5 (sandbox consultivo).

Garantías de diseño:
  * Desactivado por defecto (``NGFS_UASI_HABILITADO=false``).
  * Solo devuelve análisis/recomendaciones consultivas; no tiene acceso a la sesión
    de base de datos ni a la máquina de estados, por lo que no puede cambiar estados.
  * Defensivo: cualquier error (red, tiempo de espera, respuesta no JSON, etc.) se
    convierte en un resultado ``disponible=False``; nunca propaga excepciones.
  * Solo envía un resumen mínimo del expediente (sin datos personales del solicitante).

Nota: el contrato del endpoint de UASI v5 para NGFS (``NGFS_UASI_RUTA_ANALISIS``)
aún no está definido en UASI v5; queda pendiente (ver docs/hoja_de_ruta.md, fase 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from ngfs.config import Configuracion

log = logging.getLogger("ngfs.uasi")

AVISO_CONSULTIVO = (
    "Resultado consultivo generado por un sistema automatizado. No constituye una decisión: "
    "toda transición de estado requiere revisión y aprobación humana en NGFS."
)


@dataclass
class ResultadoUASI:
    disponible: bool
    motivo: str = ""
    recomendaciones: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {
            "disponible": self.disponible,
            "motivo": self.motivo,
            "recomendaciones": self.recomendaciones,
            "caracter": "consultivo",
            "aviso": AVISO_CONSULTIVO,
        }


class AdaptadorUASI:
    def __init__(self, cfg: Configuracion, transporte: httpx.BaseTransport | None = None) -> None:
        self._cfg = cfg
        self._transporte = transporte

    @property
    def habilitado(self) -> bool:
        return self._cfg.uasi_habilitado

    def analizar(self, resumen_expediente: dict[str, Any]) -> ResultadoUASI:
        if not self.habilitado:
            return ResultadoUASI(False, "Adaptador UASI desactivado (NGFS_UASI_HABILITADO=false).")
        cabeceras = {"Authorization": f"Bearer {self._cfg.uasi_token}"} if self._cfg.uasi_token else {}
        try:
            with httpx.Client(
                base_url=self._cfg.uasi_url,
                timeout=self._cfg.uasi_timeout_segundos,
                transport=self._transporte,
                headers=cabeceras,
            ) as cliente:
                resp = cliente.post(self._cfg.uasi_ruta_analisis, json={"origen": "NGFS", "expediente": resumen_expediente})
                resp.raise_for_status()
                cuerpo = resp.json()
            if not isinstance(cuerpo, dict):
                return ResultadoUASI(False, "Respuesta de UASI con formato inesperado.")
            return ResultadoUASI(True, "", cuerpo)
        except Exception as exc:  # noqa: BLE001 - el adaptador nunca debe romper NGFS
            log.warning("Adaptador UASI no disponible: %s", exc.__class__.__name__)
            return ResultadoUASI(False, f"UASI no disponible ({exc.__class__.__name__}).")
