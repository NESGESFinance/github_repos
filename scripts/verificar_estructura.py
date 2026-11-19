"""Comprueba sin dependencias la integridad de la reorganización (Python 3.11+)."""

from __future__ import annotations

import ast
import csv
import hashlib
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTOS = {"ngfsistem": "ngfs", "uasi-v5": "uasi_v5"}


def verificar() -> list[str]:
    errores: list[str] = []
    with (RAIZ / "docs/mapa_archivos.csv").open(newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    if len(filas) != 126:
        errores.append(f"Inventario incompleto: se esperaban 126 archivos, hay {len(filas)}")
    origenes: set[str] = set()
    destinos: set[str] = set()
    for fila in filas:
        origen, destino = fila["origen_en_main"], fila["destino"]
        if origen in origenes or destino in destinos:
            errores.append(f"Movimiento duplicado: {origen} → {destino}")
        origenes.add(origen)
        destinos.add(destino)
        ruta = RAIZ / destino
        if not ruta.is_file():
            errores.append(f"Falta el archivo: {destino}")
        elif hashlib.sha256(ruta.read_bytes()).hexdigest() != fila["sha256_original"]:
            errores.append(f"Contenido original alterado: {destino}")

    for proyecto, paquete in PROYECTOS.items():
        base = RAIZ / "apps" / proyecto
        with (base / "pyproject.toml").open("rb") as archivo:
            config = tomllib.load(archivo)
        for carpeta in config["tool"]["setuptools"]["packages"]["find"]["where"]:
            if not (base / carpeta).is_dir():
                errores.append(f"Directorio de empaquetado inexistente: {base / carpeta}")
        src = base / "src"
        if not (src / paquete / "__init__.py").is_file():
            errores.append(f"Falta el inicializador del paquete {paquete}")
        rutas = (sorted((src / paquete).rglob("*.py"))
                 + sorted((base / "tests").rglob("*.py"))
                 + sorted((base / "clientes").rglob("*.py")))
        for ruta in rutas:
            try:
                arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
            except SyntaxError as exc:
                errores.append(f"Sintaxis inválida: {exc}")
                continue
            if ruta.is_relative_to(src) and not (ruta.parent / "__init__.py").is_file():
                errores.append(f"Falta __init__.py en {ruta.parent.relative_to(RAIZ)}")
            modulos = []
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                    modulos.append(nodo.module)
                elif isinstance(nodo, ast.Import):
                    modulos.extend(alias.name for alias in nodo.names)
            for modulo in modulos:
                if modulo == paquete or modulo.startswith(paquete + "."):
                    destino_modulo = src.joinpath(*modulo.split("."))
                    if not (destino_modulo.with_suffix(".py").is_file()
                            or (destino_modulo / "__init__.py").is_file()):
                        errores.append(f"Import interno sin destino: {modulo} en {ruta.relative_to(RAIZ)}")
    return errores


if __name__ == "__main__":
    problemas = verificar()
    if problemas:
        print("\n".join(problemas), file=sys.stderr)
        sys.exit(1)
    print("OK: 126 archivos originales conservados; paquetes, sintaxis e imports internos coherentes.")
