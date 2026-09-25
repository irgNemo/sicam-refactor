# SICAM Refactor

SICAM (Sistema de Captura y Análisis de Micronúcleos) reúne una aplicación
Django REST + Vue/Vite y tres servicios de segmentación en un monorepo.

```text
apps/web/Frontend             Vue/Vite :5173
           -> apps/web/Backend          Django :8000
                 +-> apps/segmentation-saliva      CURRENT :8001
                 +-> apps/segmentation-blood       BLOOD   :8002
                 +-> apps/segmentation-saliva-alt  ALT     :8003
```

El flujo integrado permite registrar pacientes/casos/muestras, segmentar,
persistir resultados, consultar históricos, editar y validar revisiones y
caracterizar el resultado efectivo en Django. SALIVA dispone de selector:
**Modelo SICAM** (`CURRENT_CUSTOM_V1`, default) o **Cellpose-SAM alternativo**
(`ALT_CPSAM_MORPHOLOGICAL_V1`). BLOOD sigue independiente, sin selección de
estrategias. SALIVA v2 expone morfometría; BLOOD conserva conteos v1.
No se presenta ALT como una mejora científicamente validada.

## Instalar y operar

1. [Instalación inicial en WSL](docs/developer_environment_setup_wsl.md):
   tres ambientes Conda, Node, dependencias, modelos externos, `.env` y migraciones.
2. [Arranque cotidiano y datos de prueba](docs/30_developer_startup_and_test_data.md):
   cinco terminales para el stack completo, subconjuntos por flujo y checks HTTP.

| Componente | Documentación específica |
|---|---|
| Django | [Backend](apps/web/Backend/README_DEVELOPMENT.md) |
| Vue/Vite | [Frontend](apps/web/Frontend/README.md) |
| SALIVA CURRENT | [Servicio CURRENT](apps/segmentation-saliva/README.md) |
| BLOOD | [Servicio BLOOD](apps/segmentation-blood/README.md) |
| SALIVA ALT | [Servicio ALT](apps/segmentation-saliva-alt/README.md) |

**BLOOD arranca con `main:app` desde su directorio**, porque su `main.py` está
en la raíz. CURRENT y ALT usan `app.main:app`.

## Estado y evidencia

Instalación Windows → WSL validada; estrategias SALIVA integradas en backend
y frontend. La revisión visual pendiente registrada en Sprint 18C sigue siendo
un pendiente de aceptación, no una integración ausente. Reportes/exportación
web no se declaran completados por esta actualización documental.

Los reportes de sprints, inventarios iniciales y documentos `PHASE_*` conservan
la evidencia de sus fechas; no son instrucciones actuales de instalación.
Consultar [18A](docs/58_sprint_18a_alt_saliva_segmentation_service.md),
[18B](docs/59_sprint_18b_backend_saliva_segmentation_strategies.md),
[18C](docs/60_sprint_18c_frontend_saliva_strategy_selector.md) y la
[auditoría documental 18C.1](docs/61_documentation_installation_startup_refresh.md).

Modelos, `.env`, bases, `media/`, imágenes reales y artefactos generados no se
versionan. Los modelos deben provisionarse por los mecanismos documentados;
no forman parte de un clone del repositorio.
