# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| 0.1.x (prototipo) | Correcciones de seguridad en `main`; **no usar en producción** |

## Cómo reportar una vulnerabilidad

**No abra un issue público.** Use la función *Report a vulnerability* (GitHub Security Advisories) de este
repositorio o contacte de forma privada con los responsables de NESGESFinance a través de los canales oficiales
indicados en la [documentación](https://github.com/NESGESFinance/Documentacion).

Incluya: descripción, pasos para reproducir, impacto estimado y versión/commit afectado. Intentaremos acusar recibo en
un plazo de 5 días hábiles y acordar una fecha de divulgación coordinada.

## Medidas implementadas en v0.1

- Contraseñas con bcrypt; política mínima de longitud y composición.
- JWT firmados (HS256) con expiración; en `produccion` se exige un secreto de al menos 32 caracteres.
- Bloqueo temporal de cuentas tras intentos fallidos; tiempo de respuesta homogéneo para usuarios inexistentes.
- Invalidación de tokens al cambiar el rol o desactivar al usuario.
- RBAC por etapa; respuestas `404` para recursos no visibles (no se revela su existencia).
- Bitácora encadenada SHA-256 verificable; bloqueo de modificación/borrado en la aplicación.
- Documentos procesados en streaming con límite de tamaño; no se almacena su contenido.
- Adaptador UASI desactivado por defecto, con timeout y sin datos personales del solicitante.

## Limitaciones conocidas

- Sin rate limiting global, sin revocación explícita de tokens ni tokens de refresco.
- La inmutabilidad de la bitácora no se impone aún a nivel de base de datos.
- Sin cifrado de datos en reposo gestionado por la aplicación.

Ver [docs/hoja_de_ruta.md](docs/hoja_de_ruta.md) (fases 3 y 7).
