# Control de acceso por roles (RBAC) — NGFS v0.1

> Fuente única de verdad: `src/ngfs/rbac.py` (generada con `python -m ngfs.rbac`). Un test verifica que la
> matriz de este documento coincide con el código. También disponible en la API: `GET /meta/rbac`.

## Roles

| Rol (valor API) | Nombre | Responsabilidad |
|---|---|---|
| `solicitante` | Solicitante / Promotor | Crea y edita sus expedientes en Borrador, adjunta documentos, envía. Solo ve **sus** expedientes. |
| `analista` | Analista | Revisión documental y análisis técnico/financiero; puede solicitar análisis consultivo UASI. |
| `cumplimiento` | Oficial de Cumplimiento | Revisión de cumplimiento; puede devolver a análisis; consulta la bitácora. |
| `comite` | Comité / Aprobador | Única instancia que **decide** (aprobar/rechazar) con confirmación humana; cierra expedientes. |
| `auditor` | Auditor | **Solo lectura** de todo, incluida la bitácora y su verificación de integridad. |
| `administrador` | Administrador | Gestión de usuarios y archivo administrativo de expedientes rechazados. No decide. |

## Matriz rol × etapa × acción

Acciones de etapa: `ver`, `editar`, `adjuntar_documento`, `consultar_uasi` y las acciones de transición
(ver [maquina_estados.md](maquina_estados.md)).

| Rol \ Estado | borrador | enviado | revision_documental | en_analisis | revision_cumplimiento | aprobado | rechazado | en_ejecucion | cerrado |
|---|---|---|---|---|---|---|---|---|---|
| **solicitante** | adjuntar_documento, editar, enviar, ver | ver | ver | ver | ver | ver | ver | adjuntar_documento, ver | ver |
| **analista** | — | iniciar_revision, ver | aceptar_documentacion, adjuntar_documento, devolver_a_solicitante, ver | adjuntar_documento, consultar_uasi, enviar_a_cumplimiento, ver | ver | iniciar_ejecucion, ver | ver | adjuntar_documento, ver | ver |
| **cumplimiento** | — | ver | ver | consultar_uasi, ver | adjuntar_documento, consultar_uasi, devolver_a_analisis, ver | ver | ver | ver | ver |
| **comite** | — | ver | ver | ver | adjuntar_documento, aprobar, rechazar, ver | ver | archivar, ver | adjuntar_documento, cerrar, ver | ver |
| **auditor** | ver | ver | ver | ver | ver | ver | ver | ver | ver |
| **administrador** | ver | ver | ver | ver | ver | ver | archivar, ver | ver | ver |

| Acción global | Roles |
|---|---|
| crear_expediente | solicitante |
| ver_auditoria | administrador, auditor, cumplimiento |
| verificar_auditoria | administrador, auditor, cumplimiento |
| gestionar_usuarios | administrador |

## Reglas complementarias

- **Propiedad:** el `solicitante` solo accede a los expedientes que él creó; para el resto recibe `404` (no se revela
  su existencia).
- **Borradores privados:** analista, cumplimiento y comité no ven expedientes en `borrador` (`404`).
- **Segregación de funciones:** nadie puede decidir un expediente que presentó (relevante si un usuario cambia de rol).
- **Cambio de rol o desactivación:** invalida inmediatamente los tokens emitidos (`401`); hay que iniciar sesión de nuevo.
- **Administrador:** no puede modificar su propio rol/estado (evita autoescalada o bloqueo accidental).
- Respuestas: `401` sin autenticación válida, `403` acción no permitida, `404` recurso no visible.
