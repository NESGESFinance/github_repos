"""Control de acceso basado en roles: matriz rol × etapa × acción.

La matriz se construye a partir de:
  * acciones de etapa (ver, editar, adjuntar_documento, consultar_uasi), y
  * las transiciones de ``ngfs.estados.TRANSICIONES`` (cada acción de transición
    está permitida solo a los roles declarados en ella).

Además existen acciones globales no ligadas a una etapa.
Ejecutar ``python -m ngfs.rbac`` imprime la matriz en Markdown (se usa en docs/rbac.md).
"""

from __future__ import annotations

from ngfs.estados import TRANSICIONES, Estado, Rol

VER = "ver"
EDITAR = "editar"
ADJUNTAR = "adjuntar_documento"
CONSULTAR_UASI = "consultar_uasi"

TODOS_LOS_ESTADOS = frozenset(Estado)
ESTADOS_NO_BORRADOR = TODOS_LOS_ESTADOS - {Estado.BORRADOR}

# Acciones de etapa: rol -> acción -> estados en los que está permitida.
_ACCIONES_ETAPA: dict[Rol, dict[str, frozenset[Estado]]] = {
    Rol.SOLICITANTE: {
        VER: TODOS_LOS_ESTADOS,  # solo sus propios expedientes (control de propiedad aparte)
        EDITAR: frozenset({Estado.BORRADOR}),
        ADJUNTAR: frozenset({Estado.BORRADOR, Estado.EN_EJECUCION}),
    },
    Rol.ANALISTA: {
        VER: ESTADOS_NO_BORRADOR,
        ADJUNTAR: frozenset({Estado.REVISION_DOCUMENTAL, Estado.EN_ANALISIS, Estado.EN_EJECUCION}),
        CONSULTAR_UASI: frozenset({Estado.EN_ANALISIS}),
    },
    Rol.CUMPLIMIENTO: {
        VER: ESTADOS_NO_BORRADOR,
        ADJUNTAR: frozenset({Estado.REVISION_CUMPLIMIENTO}),
        CONSULTAR_UASI: frozenset({Estado.EN_ANALISIS, Estado.REVISION_CUMPLIMIENTO}),
    },
    Rol.COMITE: {
        VER: ESTADOS_NO_BORRADOR,
        ADJUNTAR: frozenset({Estado.REVISION_CUMPLIMIENTO, Estado.EN_EJECUCION}),
    },
    Rol.AUDITOR: {VER: TODOS_LOS_ESTADOS},
    Rol.ADMINISTRADOR: {VER: TODOS_LOS_ESTADOS},
}

# Acciones globales (no dependen de la etapa).
CREAR_EXPEDIENTE = "crear_expediente"
VER_AUDITORIA = "ver_auditoria"
VERIFICAR_AUDITORIA = "verificar_auditoria"
GESTIONAR_USUARIOS = "gestionar_usuarios"

ACCIONES_GLOBALES: dict[str, frozenset[Rol]] = {
    CREAR_EXPEDIENTE: frozenset({Rol.SOLICITANTE}),
    VER_AUDITORIA: frozenset({Rol.AUDITOR, Rol.CUMPLIMIENTO, Rol.ADMINISTRADOR}),
    VERIFICAR_AUDITORIA: frozenset({Rol.AUDITOR, Rol.CUMPLIMIENTO, Rol.ADMINISTRADOR}),
    GESTIONAR_USUARIOS: frozenset({Rol.ADMINISTRADOR}),
}


def _construir_matriz() -> dict[Rol, dict[Estado, frozenset[str]]]:
    matriz: dict[Rol, dict[Estado, set[str]]] = {r: {e: set() for e in Estado} for r in Rol}
    for rol, acciones in _ACCIONES_ETAPA.items():
        for accion, estados in acciones.items():
            for estado in estados:
                matriz[rol][estado].add(accion)
    for t in TRANSICIONES:
        for rol in t.roles:
            matriz[rol][t.desde].add(t.accion)
    return {r: {e: frozenset(a) for e, a in fila.items()} for r, fila in matriz.items()}


MATRIZ: dict[Rol, dict[Estado, frozenset[str]]] = _construir_matriz()


def permitido(rol: Rol, estado: Estado, accion: str) -> bool:
    return accion in MATRIZ[rol][estado]


def permitido_global(rol: Rol, accion: str) -> bool:
    return rol in ACCIONES_GLOBALES.get(accion, frozenset())


def matriz_markdown() -> str:
    estados = list(Estado)
    cab = "| Rol \\ Estado | " + " | ".join(e.value for e in estados) + " |"
    sep = "|" + "---|" * (len(estados) + 1)
    filas = [cab, sep]
    for rol in Rol:
        celdas = [", ".join(sorted(MATRIZ[rol][e])) or "—" for e in estados]
        filas.append(f"| **{rol.value}** | " + " | ".join(celdas) + " |")
    filas += ["", "| Acción global | Roles |", "|---|---|"]
    for accion, roles in ACCIONES_GLOBALES.items():
        filas.append(f"| {accion} | {', '.join(sorted(r.value for r in roles))} |")
    return "\n".join(filas)


if __name__ == "__main__":  # pragma: no cover
    print(matriz_markdown())
