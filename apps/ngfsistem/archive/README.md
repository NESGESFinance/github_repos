# Metadatos históricos de NGFSistem

`ngfsistem.egg-info/` conserva los seis archivos de metadatos de distribución que estaban sueltos en la raíz.
Son una instantánea anterior a la reorganización, no código fuente ni configuración activa. Sus referencias
se conservan tal como estaban para mantener la trazabilidad.

La instalación y la construcción del paquete usan `../pyproject.toml` y `../src/ngfs/`; setuptools genera sus
propios metadatos nuevos en `../src/ngfsistem.egg-info/` (ignorados por Git). No copie el archivo histórico
`SOURCES.txt` al paquete ni lo use como manifiesto de construcción.
