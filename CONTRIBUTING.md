# Cómo contribuir a NGFSistem

Gracias por su interés. NGFS es la capa de gestión y auditoría de NESGESFinance, por lo que priorizamos la
**seguridad, la trazabilidad y la claridad** sobre la velocidad.

## Flujo de trabajo

1. Cree una rama desde `main`: `feature/<descripcion>` o `fix/<descripcion>`.
2. Instale el entorno: `pip install -e ".[dev]"`.
3. Antes de abrir un Pull Request, ejecute y deje en verde:
   ```bash
   ruff check .
   mypy
   pytest
   ```
4. Abra el PR con una descripción en español: qué cambia, por qué, cómo se probó y qué criterios AC afecta.
5. Todo cambio requiere revisión de al menos una persona distinta del autor. No se hace merge directo a `main`.

## Reglas de diseño (no negociables)

- **Supervisión humana:** ninguna ruta, tarea o integración puede ejecutar `aprobar`/`rechazar` automáticamente.
- **Fuente única de verdad:** la máquina de estados vive en `src/ngfs/estados.py` y la matriz en `src/ngfs/rbac.py`.
  Si las cambia, actualice `docs/maquina_estados.md` y `docs/rbac.md` (los tests verifican que coinciden).
- **Auditoría:** toda acción que modifique datos debe registrar un evento con `registrar_evento`.
- **UASI aislado:** el adaptador no debe recibir sesiones de BD ni poder modificar expedientes.
- **Sin secretos** en el código ni en el historial de Git. Use `.env` (ignorado) y `.env.example` como plantilla.
- **Transparencia:** no documente funcionalidades que no existan; marque lo planificado como tal.

## Estilo

- Código, identificadores y documentación en español (salvo términos técnicos estándar).
- Tipado completo (mypy estricto) y líneas de hasta 130 caracteres (ruff).
- Mensajes de commit en español, en imperativo: `Añade verificación de ...`, `Corrige ...`.

## Marca

Use siempre "NESGESFinance" y el lema "Tokenización con Propósito". El token NGF·BTC·AM es de utilidad y
gobernanza; no lo presente como inversión.
