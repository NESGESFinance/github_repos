# Hoja de ruta de implementación — NGFSistem (7 fases)

> Documento de planificación. Las fases posteriores a la 1 son **propuestas** y no están implementadas. Las fechas
> se fijarán con el equipo de NESGESFinance.

| Fase | Nombre | Objetivo | Entregables principales | Estado |
|---|---|---|---|---|
| 1 | Prototipo funcional (v0.1) | Validar el modelo de gestión y auditoría | Máquina de estados de 8 etapas, RBAC, autenticación bcrypt+JWT, bitácora SHA-256 encadenada, documentos por hash, adaptador UASI aislado y desactivado, criterios AC-01…AC-15 (borrador), tests | ✅ Completada en este repositorio |
| 2 | Validación funcional y de gobernanza | Revisar el prototipo con el negocio | Validación de etapas, roles y matriz RBAC con Cumplimiento y Comité; criterios de aceptación definitivos; glosario; política de retención documental | ⏳ Pendiente |
| 3 | Endurecimiento técnico | Preparar el núcleo para entornos reales | Migraciones (Alembic), PostgreSQL como base por defecto en despliegue, bloqueo de UPDATE/DELETE de la bitácora a nivel de BD (triggers/permisos), control de concurrencia optimista, limitación de peticiones, registro estructurado, tokens de refresco/revocación | ⏳ Pendiente |
| 4 | Gobernanza avanzada | Reflejar la toma de decisiones real | Decisiones colegiadas del Comité (quórum, votos, conflictos de interés), firmas electrónicas de actas, almacenamiento cifrado de documentos (además de la huella), notificaciones | ⏳ Pendiente |
| 5 | Integración UASI v5 (sandbox) | Análisis consultivo controlado | Contrato de API acordado con UASI v5 para análisis de expedientes, pruebas en entorno aislado, evaluación de sesgos y explicabilidad, registro del modelo/versión usado en cada análisis. Siempre consultivo y con supervisión humana | ⏳ Pendiente |
| 6 | Integración con el ecosistema NESGESFinance | Conectar NGFS con el resto de componentes | Integración con NESGESFinanceTrust, anclaje periódico de la raíz de la bitácora (p. ej. OpenTimestamps, como en UASI v5), interfaz web para los roles, enlace a la documentación oficial | ⏳ Pendiente |
| 7 | Auditoría externa y puesta en producción | Operar con garantías | Auditoría de seguridad independiente, pruebas de penetración, revisión legal/regulatoria (Ecuador y EE. UU.), plan de continuidad, despliegue productivo y monitoreo | ⏳ Pendiente |

## Principios transversales

- **Supervisión humana obligatoria**: ningún componente automatizado decide sobre un expediente.
- **Transparencia radical**: cada cambio queda en la bitácora verificable.
- **Mínimo privilegio** y segregación de funciones.
- **Sin promesas financieras**: el token NGF·BTC·AM (Rune #208,645) es exclusivamente de utilidad y gobernanza; NGFS
  no lo gestiona en v0.1 y no se presenta como instrumento de inversión.
