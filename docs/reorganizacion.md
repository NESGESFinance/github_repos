# Reorganización y validación

## Causa y criterio

El repositorio contenía dos distribuciones Python aplanadas en la raíz. Ambos `pyproject.toml` buscaban
paquetes en `src/`, pero esa carpeta no existía. Se reprodujo el error del backend setuptools:
`error in 'egg_base' option: 'src' does not exist or is not a directory`.

Los imports, los docstrings de los 15 inicializadores, el árbol del README de UASI y el manifiesto histórico
`SOURCES.txt` de NGFS permiten identificar la estructura de origen. Se separaron en dos aplicaciones:

- `apps/ngfsistem/`: paquete `ngfs`, pruebas, docs, configuración, licencia Apache-2.0 y avisos NGFS.
- `apps/uasi-v5/`: paquete `uasi_v5` por capas, pruebas, clientes, scripts, Docker, docs y licencia MIT.
- `docs/`: ensayo compartido y mapa de los movimientos.

El [CSV](mapa_archivos.csv) contiene los 126 archivos que estaban versionados en `main` antes del cambio.
125 se movieron; `.abacus.donotdelete` permanece en la raíz. Ninguno cambió de contenido ni se eliminó.
Los scripts de UASI ahora tienen permiso de ejecución para que funcionen las invocaciones `./scripts/...`
ya descritas por su README y Makefile.

No se combinaron las dos configuraciones de pytest ni sus dependencias: tienen fixtures y requisitos
independientes. Los seis metadatos de instalación NGFS heredados se archivaron, no se usan para construir.
La configuración local `mise.local.toml` generada por las herramientas no estaba versionada y no se publica.

## Verificaciones realizadas (Python 3.11)

| Comprobación | Resultado |
|---|---|
| Inventario contra el árbol Git original y SHA-256 | 126/126 archivos conservados, contenido idéntico |
| `python3 scripts/verificar_estructura.py` | Correcto: integridad, sintaxis Python e imports internos estáticos |
| Instalación editable de cada aplicación | Correcta |
| NGFS: `pytest` | 39 pruebas aprobadas |
| UASI: `UASI_TEST_OTS_RED=0 pytest` | 46 aprobadas; 1 omitida por requerir calendarios externos |
| NGFS: `ruff check .` y `mypy` | Correctos; 18 módulos comprobados por mypy |
| UASI: `mypy` | Correcto; 55 módulos comprobados |
| UASI: `ruff check src tests` | 15 incidencias heredadas; no se alteró el código ni la configuración que las produce |
| `ruff check --isolated scripts/verificar_estructura.py` | Correcto |
| `bash -n` sobre los tres scripts de UASI | Correcto |
| Distribuciones `sdist` y `wheel` de ambas aplicaciones | Construcción correcta |
| Contenido de los wheels | Incluyen los 18 módulos NGFS y 55 módulos UASI esperados |
| Wheels instalados, fuera del repositorio, con TestClient | `/salud` de NGFS y `/api/v5/health` de UASI responden HTTP 200 |

Los avisos de UASI se verificaron sobre los archivos originales sin cambios (por ejemplo, reglas de
modernización `UP015`, `UP017`, `UP037` y uso de `zip` sin `strict`, `B905`). No se ocultaron reglas ni se
hicieron arreglos de estilo o negocio fuera del alcance solicitado. El backend conserva la advertencia
heredada sobre `project.license` como tabla TOML. TestClient también emite un aviso de deprecación sobre httpx.

## Límites y trabajo separado

- No se ejecutaron contenedores Docker, pruebas reales de OpenTimestamps ni validaciones TypeScript del cliente.
- Se conserva `DEPLOY_README.md` de UASI como documento heredado de v5.1; sus nombres del monolito no son
  las entradas modulares actuales. La guía actual de uso está en el README de cada aplicación.
- NGFS sigue siendo un prototipo, no apto para datos reales según su propia documentación. La integración
  consultiva NGFS → UASI sigue pendiente de contrato; este cambio no la implementa.
- No se modificaron permisos, variables, dominio, directorio raíz ni despliegues de Vercel. El repositorio
  pasa a ser explícitamente multiaplicación: antes de desplegar hay que elegir la aplicación y usar su
  directorio como raíz de construcción. No hay una aplicación instalable en la raíz común.
- Los cambios se proponen mediante PR para revisión humana; no se hace merge directo a `main`.
