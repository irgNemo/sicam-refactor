# Sprint 18R-C — Rediseño visual y ergonómico de Registro

## Baseline y alcance

- Rama: `master`.
- HEAD inicial: `c7831434886b79e6dc42ccd19520d29425bb264d`.
- Working tree inicialmente limpio, después del cierre de 18R-B.
- Cambios de presentación frontend, pruebas y este documento.
- Sin cambios en backend, modelos, endpoints, payloads, microservicios ni
  dependencias. Sin altas reales ni operaciones sobre BD/media.
- Sin staging, commit ni push.

## Problema anterior

Registro usaba un wrapper limitado a 900 px sin centrado, una clase genérica
`content` sin layout local propio y botones primarios sin estilo base local.
Las pestañas y formularios tenían jerarquía y espaciados distintos de
Segmentación. Los labels no estaban asociados a sus campos y los errores DRF
se presentaban principalmente en una notificación global.

Las miniaturas cuadradas y el listado separado de resultados dificultaban
relacionar archivo, preview, estado y error. Los selectores dependientes
aparecían progresivamente y el contexto de destino no tenía un resumen.

## Nueva estructura

- Contenedor centrado de máximo **960 px**, ancho flexible y padding de 24 px.
- Cabecera «Registro de datos» y subtítulo breve.
- Navegación **Paciente / Caso / Imágenes**, con estado activo visible.
- Una tarjeta principal por sección, fondo blanco, borde/sombra suaves,
  cabecera y footer de acciones.
- Tipografía global conservada; azul, radios de 8/10/12 px y espaciados de
  8/12/16/24 px coherentes con los controles de Segmentación.
- Limpiar como acción secundaria; submit como acción primaria.
- Sin extracción de componentes ni refactor arquitectónico.

### Paciente

Grid de dos columnas con el siguiente orden visual y de teclado:

1. Identificación.
2. Fecha de nacimiento.
3. Nombre.
4. Apellido.
5. Email.
6. Teléfono.

Se conservan los cuatro primeros campos obligatorios y los dos últimos
opcionales. Cada campo tiene label visible asociado mediante `for/id`.
Los errores conocidos DRF se muestran debajo del campo con `aria-invalid` y
`aria-describedby`; se mantiene también la notificación global.

### Caso

Paciente, título, descripción y checkbox «Crear análisis automáticamente».
La explicación indica que se creará un análisis asociado al nuevo caso.
Si el usuario selecciona el paciente recién creado, se señala ese contexto;
no se fuerza la selección ni se cambia automáticamente de pestaña.

Los errores del paciente admiten las claves existentes `paciente` e
`id_paciente_fk`; título y descripción tienen mensajes locales. Errores
generales o del análisis se presentan al pie del formulario y en el toast.

El checkbox mantiene su valor inicial y el endpoint atómico de 18R-B cuando
está seleccionado. No hay cambios de contratos ni operación transaccional.

### Imágenes

Se agrupan los controles en Contexto, Tipo de muestra, Archivos y Estado de carga:

- Paciente/Caso/Análisis permanecen visibles, con labels, estados vacíos,
  loading y bloqueo cuando falta el contexto padre.
- El resumen muestra únicamente los datos ya seleccionados:
  paciente, caso, número de análisis y tipo.
- SALIVA/SANGRE se presentan como opciones segmentadas con radios nativos;
  conservan valores, `v-model` y handler de cambio.
- Selector real de múltiples archivos. No se simula ni añade drag-and-drop.
- Cada archivo reúne miniatura, nombre, badge de estado y error.
- Se conserva «Vista previa no disponible» cuando falla la miniatura.
- Estados: Pendiente, Subiendo..., Subida y Error.
- El botón muestra «Reintentar fallidos» cuando los únicos archivos pendientes
  de envío son ERROR. El handler existente sigue enviando exclusivamente
  PENDING/ERROR, nunca los SUCCESS confirmados.
- «Quitar de la lista» describe la operación local; no borra muestras del servidor.

## Estado y comportamiento conservados

Las adiciones al script se limitan a presentación:

- `isLoadingPatients` para hacer visible el GET de pacientes.
- `patientErrors` y `caseErrors` para presentar errores por campo y limpiarlos
  al reenviar o limpiar el formulario.
- Computed de contexto seleccionado y texto del botón de upload.
- `registrationFieldErrors()` extrae los mismos campos, strings y límites
  aceptados por el formatter previo. El mensaje global conserva su formato.
  No se muestran campos desconocidos, tracebacks ni HTML ejecutable.

Se conservan y prueban:

- creación de paciente y refresco de lista;
- Caso con/sin análisis y payload atómico;
- guard de doble submit y bloqueo durante escritura;
- subida secuencial, éxito parcial y reintento de fallidos;
- limpieza de hijos, generaciones y rechazo de respuestas obsoletas;
- liberación de object URLs al cambiar contexto, quitar, limpiar o desmontar;
- confirmación dirty al cambiar sección y al salir de Registro;
- `beforeunload`, conservación de formularios al confirmar navegación y
  limpieza de listener/timer al desmontar.

Las secciones siguen siendo independientes: pueden utilizarse pacientes y
casos existentes sin crear registros en esta sesión. No hay wizard ni autoavance.
No cambia la lógica de Segmentación/editor, effective ni Characterization.

## Responsive y accesibilidad

- Hasta 767 px, los grids de campos y contexto pasan a una columna y el
  padding baja a 16 px.
- Hasta 479 px, las acciones se apilan y el resumen usa una columna.
- Previews con grid adaptable, nombres que envuelven texto y `min-width: 0`.
- Labels asociados, inputs/selects/botones nativos, radios agrupados,
  legends accesibles y foco visible.
- Se conservan fieldsets deshabilitados y `aria-busy` durante escrituras.
- Loading con texto; estados por archivo con texto además del color.
- Notificaciones con `role=status/alert` y botón de cierre etiquetado.

Se reemplazan exclusivamente estilos locales obsoletos de tabs, wrapper,
formulario, preview y notificación. Se añade un layout local específico
`registration-content`; no hay limpieza CSS global.

## Validaciones

Ejecutadas desde `apps/web/Frontend` con **Node 24.17.0**, sin instalaciones:

| Comando | Resultado |
| --- | --- |
| `node tests/registration.test.mjs` | **24 passed** |
| `node tests/segmentationStrategies.test.mjs` | **59 passed** |
| `node tests/characterization21.test.mjs` | **22 passed** |
| `npm run build` | **PASS**, 106 módulos |
| `git diff --check` | **PASS** |

Se conservan las 18 pruebas existentes de Registro y se añaden seis de
presentación: navegación activa, orden/labels/required, errores inline
escapados y limpieza, Caso, loading/selectores vacíos y contexto/previews/
estados/reintento. Usan SSR y adaptadores HTTP simulados, sin persistir datos.
No son pruebas por píxel ni aceptación en navegador.

No se encontró Chromium, Chrome ni Firefox disponible en PATH. La inspección
visual humana queda pendiente:

- [ ] Nuevo paciente en escritorio y laptop.
- [ ] Nuevo caso y explicación del checkbox.
- [ ] Imágenes con contexto y tipo claramente visibles.
- [ ] Errores por campo y notificación.
- [ ] Estados de carga y controles deshabilitados.
- [ ] Upload con éxito/error, fallback y reintento.
- [ ] Viewport estrecho sin overflow y acciones apiladas.
- [ ] Recorrido de teclado y foco visible.

## Archivos

- `apps/web/Frontend/src/views/RegistroView.vue`
- `apps/web/Frontend/src/services/registrationErrors.js`
- `apps/web/Frontend/tests/registration.test.mjs`
- `docs/77_sprint_18r_c_registration_ui.md`

## Decisiones no implementadas

Continúan las decisiones pendientes documentadas en 18R-B: UI de pacientes
pseudonimizados, `case_number`, control del estado del análisis, política de
uploads a análisis cerrados, validación adicional de fecha futura,
idempotencia durable del upload y creación posterior de análisis desde
Registro para un caso sin análisis. No se agregan campos ni reglas.

La revisión visual queda pendiente; las comprobaciones automatizadas pasan.

**SPRINT 18R-C = READY_FOR_VISUAL_REVIEW**
