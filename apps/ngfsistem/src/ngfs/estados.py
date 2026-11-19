"""Máquina de estados de expedientes (8 etapas) y roles del sistema.

La etapa 6 ("Decisión") tiene dos estados de resultado: APROBADO y RECHAZADO.
Las transiciones de decisión requieren SIEMPRE confirmación humana explícita y
justificación; ningún componente automático (incluido el adaptador UASI) puede
ejecutarlas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Rol(StrEnum):
    SOLICITANTE = "solicitante"
    ANALISTA = "analista"
    CUMPLIMIENTO = "cumplimiento"
    COMITE = "comite"
    AUDITOR = "auditor"
    ADMINISTRADOR = "administrador"


class Estado(StrEnum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    REVISION_DOCUMENTAL = "revision_documental"
    EN_ANALISIS = "en_analisis"
    REVISION_CUMPLIMIENTO = "revision_cumplimiento"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    EN_EJECUCION = "en_ejecucion"
    CERRADO = "cerrado"


# Estado -> (número de etapa, nombre legible de la etapa)
ETAPAS: dict[Estado, tuple[int, str]] = {
    Estado.BORRADOR: (1, "Borrador"),
    Estado.ENVIADO: (2, "Enviado"),
    Estado.REVISION_DOCUMENTAL: (3, "En revisión documental"),
    Estado.EN_ANALISIS: (4, "En análisis técnico/financiero"),
    Estado.REVISION_CUMPLIMIENTO: (5, "En revisión de cumplimiento"),
    Estado.APROBADO: (6, "Decisión: Aprobado"),
    Estado.RECHAZADO: (6, "Decisión: Rechazado"),
    Estado.EN_EJECUCION: (7, "En ejecución / seguimiento"),
    Estado.CERRADO: (8, "Cerrado / Archivado"),
}


@dataclass(frozen=True)
class Transicion:
    accion: str
    desde: Estado
    hacia: Estado
    roles: frozenset[Rol]
    decision_humana: bool = False
    requiere_justificacion: bool = False
    descripcion: str = ""


TRANSICIONES: tuple[Transicion, ...] = (
    Transicion("enviar", Estado.BORRADOR, Estado.ENVIADO, frozenset({Rol.SOLICITANTE}),
               descripcion="El solicitante envía el expediente para revisión."),
    Transicion("iniciar_revision", Estado.ENVIADO, Estado.REVISION_DOCUMENTAL, frozenset({Rol.ANALISTA}),
               descripcion="Un analista toma el expediente para revisar la documentación."),
    Transicion("devolver_a_solicitante", Estado.REVISION_DOCUMENTAL, Estado.BORRADOR, frozenset({Rol.ANALISTA}),
               requiere_justificacion=True, descripcion="Documentación incompleta: vuelve a Borrador para subsanar."),
    Transicion("aceptar_documentacion", Estado.REVISION_DOCUMENTAL, Estado.EN_ANALISIS, frozenset({Rol.ANALISTA}),
               descripcion="Documentación completa: pasa a análisis técnico/financiero."),
    Transicion("enviar_a_cumplimiento", Estado.EN_ANALISIS, Estado.REVISION_CUMPLIMIENTO, frozenset({Rol.ANALISTA}),
               descripcion="Análisis concluido: pasa a revisión de cumplimiento."),
    Transicion("devolver_a_analisis", Estado.REVISION_CUMPLIMIENTO, Estado.EN_ANALISIS, frozenset({Rol.CUMPLIMIENTO}),
               requiere_justificacion=True, descripcion="Cumplimiento solicita ampliar el análisis."),
    Transicion("aprobar", Estado.REVISION_CUMPLIMIENTO, Estado.APROBADO, frozenset({Rol.COMITE}),
               decision_humana=True, requiere_justificacion=True,
               descripcion="Decisión humana del Comité: aprobación."),
    Transicion("rechazar", Estado.REVISION_CUMPLIMIENTO, Estado.RECHAZADO, frozenset({Rol.COMITE}),
               decision_humana=True, requiere_justificacion=True,
               descripcion="Decisión humana del Comité: rechazo."),
    Transicion("iniciar_ejecucion", Estado.APROBADO, Estado.EN_EJECUCION, frozenset({Rol.ANALISTA}),
               descripcion="Inicio de ejecución y seguimiento del expediente aprobado."),
    Transicion("cerrar", Estado.EN_EJECUCION, Estado.CERRADO, frozenset({Rol.COMITE}),
               requiere_justificacion=True, descripcion="Cierre del expediente tras su ejecución."),
    Transicion("archivar", Estado.RECHAZADO, Estado.CERRADO, frozenset({Rol.COMITE, Rol.ADMINISTRADOR}),
               requiere_justificacion=True, descripcion="Archivo del expediente rechazado."),
)

ESTADOS_FINALES: frozenset[Estado] = frozenset({Estado.CERRADO})


class TransicionInvalida(Exception):
    """La acción no existe o no es válida desde el estado actual."""


def buscar_transicion(estado_actual: Estado, accion: str) -> Transicion:
    for t in TRANSICIONES:
        if t.accion == accion and t.desde == estado_actual:
            return t
    raise TransicionInvalida(f"La acción '{accion}' no es válida desde el estado '{estado_actual.value}'.")


def transiciones_desde(estado: Estado) -> list[Transicion]:
    return [t for t in TRANSICIONES if t.desde == estado]


def diagrama_mermaid() -> str:
    """Genera el diagrama Mermaid de la máquina de estados (fuente única de verdad)."""
    lineas = ["stateDiagram-v2", "    [*] --> borrador"]
    for t in TRANSICIONES:
        marca = " (decisión humana)" if t.decision_humana else ""
        lineas.append(f"    {t.desde.value} --> {t.hacia.value}: {t.accion}{marca}")
    lineas.append("    cerrado --> [*]")
    return "\n".join(lineas)
