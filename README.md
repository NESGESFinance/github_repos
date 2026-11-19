# NESGESFinance — NGFSistem y UASI v5

**Tokenización con Propósito.** Este repositorio contiene dos aplicaciones Python independientes.
Se han restaurado las carpetas que requieren sus imports, sus pruebas y sus archivos `pyproject.toml`,
sin combinar dependencias, licencias ni lógica de negocio.

| Aplicación | Directorio | Paquete / entrada ASGI | Licencia |
|---|---|---|---|
| NGFSistem: gestión, trazabilidad y auditoría de expedientes | [`apps/ngfsistem/`](apps/ngfsistem/) | `ngfs` / `ngfs.main:app` | Apache-2.0 |
| UASI v5: agentes, aprendizaje y auditoría criptográfica | [`apps/uasi-v5/`](apps/uasi-v5/) | `uasi_v5` / `uasi_v5.main:app` | MIT |

**NGFSistem sigue siendo un prototipo no apto para producción**, según su documentación original.
El adaptador NGFS → UASI es opcional, está desactivado por defecto y su contrato de análisis sigue pendiente;
reorganizar los archivos no implementa esa integración.

## Estructura

```text
apps/
├── ngfsistem/
│   ├── src/ngfs/             # dominio, configuración, BD y API
│   ├── tests/                # pruebas y fixtures propias
│   ├── docs/                 # arquitectura, estados, RBAC y planificación
│   ├── archive/              # metadatos históricos; no se usan para instalar
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── docker-compose.yml
└── uasi-v5/
    ├── src/uasi_v5/           # capas y paquetes originales
    ├── tests/                # pruebas y fixtures propias
    ├── clientes/python/      # cliente JEV de referencia
    ├── clientes/typescript/  # cliente JEV de referencia
    ├── scripts/              # utilidades de secretos y OpenTimestamps
    ├── docker/               # Dockerfile y Compose con Redis
    ├── docs/                 # arquitectura y API
    ├── pyproject.toml
    └── Makefile
docs/                         # documento compartido y mapa de archivos
scripts/verificar_estructura.py
```

Los sufijos de descarga `(1)`, `(2)`, etc. se han eliminado al colocar cada archivo en su paquete correcto.
Los directorios Python usan `__init__.py`; las carpetas en sí no requieren extensión.

## Desarrollo y pruebas

Use Python 3.11 y **un entorno virtual distinto por aplicación**. Ejecute las herramientas desde el
subdirectorio correspondiente, no desde la raíz del monorepositorio.

### NGFSistem

```bash
cd apps/ngfsistem
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
mypy
uvicorn ngfs.main:app --port 8080
```

Para variables de entorno, administración y PostgreSQL, consulte su [README](apps/ngfsistem/README.md)
y sus [reglas de contribución](apps/ngfsistem/CONTRIBUTING.md). No use datos reales con el prototipo.

### UASI v5

```bash
cd apps/uasi-v5
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e . --no-deps
UASI_TEST_OTS_RED=0 pytest
ruff check src tests
mypy
```

Configure sus propias variables de entorno antes de arrancar el servicio; consulte el
[README de UASI](apps/uasi-v5/README.md). Los comandos `make` se ejecutan desde `apps/uasi-v5/`.
La guía `DEPLOY_README.md` se conserva como material heredado de v5.1: contiene nombres del monolito anterior;
para las rutas modulares actuales use el README de UASI (`uasi_v5.main:app`).

### Integridad de la reorganización

Desde la raíz:

```bash
python3 scripts/verificar_estructura.py
```

El [mapa de archivos](docs/mapa_archivos.csv) registra el origen, destino y SHA-256 de los 126 archivos
originales. El verificador comprueba que ninguno se perdió ni cambió de contenido, valida la sintaxis Python
y comprueba los imports internos estáticos. No sustituye las pruebas funcionales.

## Alcance

Esta reorganización no selecciona qué aplicación debe servir `ngfsystem.xyz`, no modifica la configuración
de Vercel y no despliega en producción. La raíz es ahora un índice, no una aplicación Python instalable;
los consumidores deben usar el directorio de la aplicación elegida. Las pruebas de cada proyecto deben
lanzarse por separado para mantener aisladas sus configuraciones y dependencias.

La plantilla de CI de NGFS sigue en `apps/ngfsistem/docs/ci.yml.example`: no se activa automáticamente;
al adaptarla al monorepositorio, sus comandos deben ejecutarse en `apps/ngfsistem/`.

Las políticas y avisos originales están en cada aplicación:
[seguridad de NGFS](apps/ngfsistem/SECURITY.md),
[licencia Apache-2.0](apps/ngfsistem/LICENSE), [NOTICE](apps/ngfsistem/NOTICE)
y [licencia MIT de UASI](apps/uasi-v5/LICENSE).
