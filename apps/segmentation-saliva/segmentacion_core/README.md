# Core científico SALIVA CURRENT

El servicio FastAPI llama al pipeline desde `app/services/segmentador.py`.
No ejecutar manualmente una secuencia de scripts `seg_membranas.py`,
`seg_nucleos.py` y `seg_micronucleos.py` para levantar la API.

Esta carpeta contiene el Cellpose vendorizado y los módulos científicos.
El modelo externo `membranas_500_125` debe provisionarse aquí y permanecer
ignorado por Git. Instalar y arrancar desde el
[README del microservicio](../README.md), ambiente `sicam`, puerto 8001.
No sustituir el vendorizado por Cellpose PyPI ni cambiar el pipeline durante
instalación/arranque.
