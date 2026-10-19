# Sprint 18Q-B — Retiro de controles placeholder

Estado: **READY_FOR_VISUAL_REVIEW**.
HEAD inicial: `f4273b8acdbe139ed5ea5984e657a9c2426d5523`, rama `master`.
Working tree inicialmente limpio; Sprint 18Q-A ya versionado.

## Alcance

La auditoría previa encontró cuatro controles sin handlers, una pestaña que sólo
abría un placeholder y un botón lateral que únicamente escribía en consola.
Por decisión del investigador se retiraron los seis, sin implementar funciones
nuevas ni sustituirlos por controles deshabilitados:

- Engrane/configuración y campana/notificaciones, incluido badge rojo.
- Exportar CSV y Generar PDF.
- Pestaña Análisis y su vista «En desarrollo / Próximamente».
- Ver Análisis Completo.

## Archivos y limpieza

- `TopBar.vue`: controles y contenedor de acciones eliminados, junto con sus
  estilos exclusivos. Permanecen Segmentación, Caracterización y Registro.
- `MainContent.vue`: botones de exportación y contenedor eliminados, junto con
  estilos exclusivos y reglas responsive. El layout de capas de 18Q-A se conserva.
- `SideBar.vue`: botón, método `verAnalisis`, console.log, prop
  `showAnalysisButton` y estilos scoped exclusivos eliminados.
- `App.vue`: binding retirado, sección `analisis` quitada de `VALID_SECTIONS`,
  bloque placeholder y estilos/animaciones exclusivos eliminados.
- `tests/segmentationStrategies.test.mjs`: pruebas de contexto legacy,
  navegación protegida y ausencia de controles retirados.

La búsqueda global previa distinguió la clase header-actions de Registro,
que se conserva; los estilos eliminados de MainContent eran scoped.
No quedan referencias productivas a los controles/handlers retirados.

## Contexto persistido y navegación

El formato real usa `activeTab` dentro de `sicam.uiContext.v1`.
El fallback existente comprueba `VALID_SECTIONS`: al excluir `analisis`, una
sesión anterior vuelve a `segmentacion` sin perder paciente, caso, tipo de muestra,
muestra ni resultado seleccionado. Se mantiene la versión 1 y no se borra
indiscriminadamente el contexto. Al persistir se guarda la sección corregida.

No se modificaron `requestSectionChange`, la confirmación de cambios editoriales
pendientes ni los watchers compartidos. Los tests comprueban rechazo de la sección
retirada, cancelación de navegación y navegación autorizada a secciones reales.

## Funcionalidad preservada

RegistroView y todo el backend permanecen sin cambios. Se inspeccionaron las
llamadas de Registro para crear análisis (`POST /api/analisis/`), consultar análisis
del caso y adjuntar imágenes mediante el campo `analisis`, así como sus mensajes
locales de éxito/error. El endpoint backend `cambiar_estado` sigue intacto;
no se añadió ni se afirmó un nuevo control de cambio de estado en Registro.
No se realizaron altas/subidas reales para comprobar estos flujos.

AnalisisPred, AnalisisViewSet, AnalisisSerializer y sus rutas siguen en uso.
También se conservan consultas a análisis de Segmentación, SideBar y Caracterización.
Sin cambios científicos, de API, modelos, migraciones, backend o microservicios.
Sin npm install, cambios de package.json/package-lock ni datos persistentes.

FUTURE_UI_FEATURE: CSV export; PDF report. No se muestran botones hasta que
exista una implementación real.

## Validación

Node 24.17.0, toolchain existente:

- `node tests/segmentationStrategies.test.mjs`: **48 passed**.
  Incluye tests existentes de editor, lectura, VALIDADA/BORRADOR, selección,
  segmentación selectiva y las capas de 18Q-A. Siete casos adicionales cubren
  sesiones antiguas/desconocidas/válidas, conservación del contexto, navegación
  protegida y retiro de controles.
- `node tests/characterization21.test.mjs`: **22 passed**.
- `npm run build`: **PASS**, 105 módulos transformados.
- Diff completo revisado; `git diff --check`: PASS.

Sin inspección en navegador: no hay navegador automatizado disponible en este
entorno. Se verificaron markup, render SSR, estado y eventos con la toolchain
existente. Pendiente comprobar visualmente equilibrio de TopBar, cabecera sin
espacios reservados, sidebars y Capas visibles en desktop/laptop.

Cambios limitados a cuatro componentes, un archivo de tests y este documento.
Sin commit ni push.

SPRINT 18Q-B = READY_FOR_VISUAL_REVIEW
