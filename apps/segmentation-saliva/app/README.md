# Aplicación FastAPI SALIVA CURRENT

`app/main.py` expone `app.main:app`; el router recibe `POST /segmentar`
(multipart `file`) y llama al pipeline existente.

Instalación, ambiente `sicam`, modelo, puerto 8001 y comando exacto:
[README del microservicio](../README.md).
Ejecutar desde la raíz de `apps/segmentation-saliva`, no desde esta carpeta.
No instalar dependencias aisladas ni iniciar Uvicorn sin puerto explícito:
el default 8000 corresponde a Django.
