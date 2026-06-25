# SICAM Refactor

Espacio de trabajo consolidado para la refactorización de SICAM (Sistema de Captura y Análisis de Micronúcleos).

## Estructura del Proyecto

```
sicam-refactor/
├── apps/                          # Aplicaciones consolidadas
│   ├── web/                       # Aplicación web integrada (Django + Vue)
│   ├── segmentation-saliva/       # Microservicio de segmentación de muestras salivales
│   └── segmentation-blood/        # Microservicio de segmentación de muestras de sangre
├── docs/                          # Documentación del proyecto
│   ├── ADR/                       # Architecture Decision Records
│   ├── *_inventory.md             # Inventarios de componentes
│   ├── *_domain_model.md          # Modelos de dominio
│   └── codex_master_context.md    # Contexto maestro del proyecto
├── scripts/                       # Scripts de utilidad y automatización
├── docker/                        # Archivos Docker para containerización
├── .gitignore                     # Configuración de Git
└── README.md                      # Este archivo
```

## Descripción de Aplicaciones

### apps/web/
Aplicación web consolidada que integra:
- **Backend**: Django REST API para la gestión de muestras y análisis
- **Frontend**: Interfaz Vue.js para visualización y entrada de datos
- **Base de datos**: SQLite para almacenamiento local

### apps/segmentation-saliva/
Microservicio FastAPI para segmentación de muestras salivales usando:
- Algoritmos de procesamiento de imagen personalizados
- Modelos de visión por computadora (cellpose)
- Detección de micronúcleos

### apps/segmentation-blood/
Microservicio FastAPI para segmentación de muestras de sangre usando:
- Algoritmos de segmentación especializados
- Detección de células y anomalías
- Análisis cuantitativo

## Propósito

Este directorio es el repositorio Git principal para la versión refactorizada de SICAM.
Todas las mejoras, refactorizaciones y nuevas características se desarrollarán dentro
de esta estructura consolidada.

## Directorios Originales

Los directorios originales (`micronucleos-web/`, `Segmentacion_web/`, `segmentacion_sangre/`)
se conservan como referencias y no deben ser modificados.

## Comenzar

1. Instalar dependencias de cada aplicación según sea necesario
2. Configurar variables de entorno
3. Ejecutar migraciones de base de datos (si aplica)
4. Iniciar los servicios según la documentación de cada app

## Documentación

Consulte la carpeta `docs/` para:
- Arquitectura general del sistema
- Decisiones arquitectónicas (ADR)
- Inventarios de componentes
- Modelos de dominio
- Análisis de brechas de integración

---

**Estado**: Refactorización en progreso

**Última actualización**: 2026-06-24
