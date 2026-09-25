# Sprint 18C.1 — Consolidación de instalación y arranque

Auditoría documental del **2026-09-25**. Inicio limpio en `master`, HEAD
`1487569e9bd525aaf1a76d3e4bdf5bfff0781990`. Sin cambios funcionales, instalaciones,
descargas, inferencias, staging, commit ni push.

## Inventario y clasificación

Se buscaron globalmente los temas de instalación, dependencias, WSL/Conda,
startup, modelos, puertos, variables y endpoints en los **83 Markdown/README
versionados**; 72 coincidieron con la búsqueda de temas y los restantes se
clasificaron por su contenido. La tabla cubre cada documento del inventario;
los rangos agrupan todos los nombres existentes con esos prefijos numéricos.

| Clase | Documentos auditados | Decisión |
|---|---|---|
| A CANONICAL_INSTALL (1) | `docs/developer_environment_setup_wsl.md` | Actualizado: instalación inicial |
| B CANONICAL_STARTUP (1) | `docs/30_developer_startup_and_test_data.md` | Actualizado: operación cotidiana |
| C COMPONENT_README (7) | `README.md`; `apps/web/Backend/README_DEVELOPMENT.md`; `apps/web/Frontend/README.md`; `apps/segmentation-saliva/README.md`; `apps/segmentation-saliva/app/README.md`; `apps/segmentation-saliva/segmentacion_core/README.md`; `apps/segmentation-saliva-alt/README.md` | Actualizados; enlaces canónicos y detalles propios |
| D ARCHITECTURE/DEPENDENCIES (4) | `apps/web/Backend/api/services/segmentation/USAGE.md`; `docs/10_codex_master_context.md`; `docs/13_architecture_baseline.md`; `docs/18_environment_and_dependencies.md` | USAGE corregido; 10/13/18 sólo aviso de referencia reemplazada, cuerpo preservado |
| D ARCHITECTURE/DEPENDENCIES (3) | `docs/ADR/ADR-001-keep-django-as-orchestrator.md`; `ADR-002-standardize-segmentation-contract.md`; `ADR-003-generalize-samples.md` en el mismo directorio | Sin cambios: registros de propuestas, no manuales de arranque |
| E HISTORICAL_SPRINT (67, incluye auditorías iniciales/fases/handoff) | `PHASE_0_SUMMARY.md`, `PHASE_2_SUMMARY.md`; `apps/web/Backend/CONFIGURACION_FASE_0.md`, `CONFIGURACION_FASE_2.md`, `VALIDACION_FASE_0.md`, `VALIDACION_FASE_2.md`; `docs/01_*` a `09_*`, `11_*`, `12_*`, `14_*` a `17_*`, `19_*` a `29_*`, `31_*` a `60_*`; `docs/CODEX_HANDOFF_SICAM.md` | Revisados/clasificados sin modificación; evidencia de su etapa |
| F IRRELEVANT_TO_SETUP | Ningún documento adicional fuera de las clases anteriores | No aplica |

El README BLOOD no existía: se crea `apps/segmentation-blood/README.md` (C).
Se crea también este registro. Total: **13 documentos existentes modificados y
2 nuevos**. Docs 58–60 quedan idénticos; no se reescriben sprints para convertirlos
en instrucciones actuales. `docs/18` es la auditoría de Sprint 1 que se ofrecía
como referencia operativa: sólo se añade un aviso hacia las guías vigentes.

## Contradicciones corregidas

- README raíz: elimina integraciones/caracterización ya implementadas de la
  lista de pendientes y enlaza las guías, sin duplicarlas.
- Guía WSL: incorpora ALT en toda la secuencia, corrige el cwd de instalación
  BLOOD (`-e .`), explica constraints ALT y sustituye estados iniciales ya resueltos.
- Manual cotidiano: Bash/WSL, cinco procesos, subconjuntos por flujo, selector
  SALIVA, migraciones dinámicas, checks reales y datos demo.
- Backend/USAGE: se retiran health inexistente, timeout BLOOD de 30 s, módulos
  de arranque inválidos, tests/rutas inventados y ejemplos de persistencia obsoletos.
- Frontend: `npm ci`, nvm/versiones y `.env`; no instalar Axios ni ejecutar fixes
  como parte del arranque.
- CURRENT: se reemplazan `cellseg`, instalaciones ad hoc y scripts del core
  por `sicam`, vendorizado y el servicio real en 8001.
- ALT: README operativo refleja integración 18B/18C y deja de depender de una
  imagen temporal de Sprint 18A como si fuese una fixture del clone.

**BLOOD = `main:app`**, confirmado contra `apps/segmentation-blood/main.py`.
La búsqueda global inicial no encontró un comando Uvicorn BLOOD con
`app.main:app ... 8002`; se conserva el comando correcto y se hace explícito
su directorio/entrypoint. Sí se retiró de USAGE un comando inválido
`python -m apps.segmentation-blood.main`. Los comandos históricos permanecen
como evidencia, no como instrucciones vigentes.

Arquitectura documentada: **Vue 5173 → Django 8000 → CURRENT 8001 / BLOOD 8002 /
ALT 8003**. Characterization en Django. Ambientes: **sicam Python 3.10.20**,
**sicam-blood Python 3.10.21**, **sicam-saliva-alt Python 3.10.20**, Node **24.17.0** /
npm **11.13.0** vía nvm.

## Comprobaciones y límites

- Rutas, tres módulos ASGI, manage.py, package files y manifiestos verificados
  sin importar aplicaciones ni cargar modelos. Bloques Bash comprobados con
  `bash -n`; enlaces locales de los documentos afectados resueltos.
- `.env.example` y settings auditados sólo en lectura: valores activos de las
  seis variables URL/timeout coinciden (CURRENT 30 s, ALT/BLOOD 240 s).
  **CONFIGURATION CHANGE REQUIRED: no** para la operación documentada.
- `natsort` BLOOD declarado; Segment Anything fijado a
  `dca509fe793f601edb92606367a655c15ac00fdf`; ALT incluye `-c constraints.txt`
  en runtime y `-r requirements.txt` en tests. No son blockers pendientes.
- Tamaño y SHA-256 de CURRENT y cpsam comprobados localmente; rutas de cache
  BLOOD/ALT compatibles. Ambos pueden compartir cpsam fuera del repo.
- Seed y argumentos verificados en código: sólo SALIVA, PNG 1×1 para galería;
  sin fixtures externas versionadas. No se ejecutó seed ni migrate.
- Versiones Python/Node/npm verificadas y `pip check` PASS en los tres ambientes.
  Pip avisó que su cache no era escribible dentro del sandbox; no hubo fallo
  de dependencias ni se cambiaron permisos.
- Persisten comentarios heredados fuera de Markdown: requirements CURRENT
  sugiere Cellpose PyPI y el docstring ALT dice que no está conectado. Quedan
  intactos por alcance; la documentación vigente explica el comportamiento real.
- CURRENT/BLOOD mantienen dependencias parcialmente sin pin. La copia confiable
  del modelo CURRENT sigue siendo un requisito externo para una WSL nueva.
  No se afirma haber repetido hoy una instalación desde cero ni los smokes.

`git diff --check`: PASS. Cambios sólo Markdown; código, tests, requirements,
package files, `.env.example`, modelos y migraciones intactos. Staging vacío.

```text
DOCUMENTATION REFRESH = PASS
```
