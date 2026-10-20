# Sprint 18Q-C — Columna derecha de Segmentación

## Baseline y alcance

- Rama: `master`.
- HEAD inicial: `2c2084f4d93bd0a14374c68453d939d531155029`.
- Working tree limpio al iniciar el sprint, después de 18Q-B.
- Cambios de presentación frontend exclusivamente. Sin cambios de backend,
  endpoints, modelos, microservicios, dependencias ni lógica científica.
- Sin staging, commit ni push.

## Auditoría previa

`MainContent.vue` coordina los datos y las acciones. `SegmentationResultPanel.vue`
presenta la columna; `SalivaSegmentationControl.vue` contiene modelo, objetos y
ejecución. Los controles editoriales permanecen en su ubicación existente en
`MainContent.vue`, fuera del panel reorganizado.

| Bloque anterior | Función e información propia | Decisión |
| --- | --- | --- |
| Segmentación | Elegir estrategia y categorías para la próxima ejecución | Grupo de acciones independiente |
| Segmentación seleccionada | Seleccionar un resultado base completado; fecha, ID y método | Conservar selector en Historial y mostrar identificación actual arriba |
| Resultado mostrado | Fuente efectiva en lectura; borrador de trabajo en edición | Integrar en Resultado actual, distinguiendo ambas fuentes |
| Revisión validada | Número y estado ya presentes en effective; fecha de validación | Consolidar número/estado y conservar fecha |
| Última segmentación | Fecha, estado, conteo bruto y método del último resultado | Resumen histórico; evitar repetirlo cuando es el seleccionado |
| Revisión pendiente | Borrador guardado y acción Continuar edición | Conservar aviso y evento |
| Respuesta de ejecución | ID, estado, tipo y conteo de la última respuesta | Integrar si coincide; conservar aparte cuando es otro resultado |

No se confundió el selector de resultados base con un selector de revisiones.
No se añadió un sistema nuevo de historial.

## Jerarquía resultante

1. **Segmentación**: modelo, categorías y ejecutar; conserva errores de ejecución
   y aviso de proceso prolongado BLOOD.
2. **Resultado actual**: resultado base, fecha y estado; fuente mostrada, información
   de validación y origen/método persistido. Tras 18Q-C.1, muestra `Tipo: SALIVA`
   o `Tipo: SANGRE`; los conteos permanecen en Resumen de Conteo.
3. **Historial**: selector existente, cantidad de resultados y resumen de última
   segmentación si aporta información diferente.

En lectura, la fuente mostrada coincide con effective. En edición se muestra el
número del borrador activo, `BORRADOR · No efectivo`, y una línea separada para
la fuente efectiva. `activeRevision` se pasa como prop de presentación; no se
modifica el editor ni el resolver.

La base MANUAL conserva `Anotación manual`. CURRENT/ALT provienen de los datos
persistidos, nunca del modelo elegido para una ejecución futura. Un método
ausente continúa usando el fallback existente. Una VALIDADA no convierte la
base en automática ni elimina el borrador pendiente.

Las acciones y sus eventos permanecen: ejecución SALIVA/BLOOD, selección de
resultado y Continuar edición. Editar, Guardar, Cancelar, Validar y undo/redo no
se modifican. Tampoco cambian requests, responses ni reglas de navegación.

## Estilos y limpieza

Se conservan tipografía, radios y colores existentes para información, borrador
y validación. Se reemplazan tarjetas repetidas por tres secciones compactas.
Se eliminan únicamente estilos de las tarjetas retiradas y su etiqueta oculta,
ahora visible. Props y métodos que siguen aportando información permanecen.

No cambia el ancho de las tres columnas ni el visor de 18Q-A. Los textos admiten
salto de línea; el selector tiene ancho limitado al panel y el botón Continuar
edición ocupa su propia fila. Los controles placeholder retirados en 18Q-B no
reaparecen. La comprobación real de overflow en desktop/laptop está pendiente.

## Archivos

- `apps/web/Frontend/src/components/segmentation/SegmentationResultPanel.vue`:
  agrupación, presentación de fuentes y estilos.
- `apps/web/Frontend/src/components/MainContent.vue`: prop `activeRevision`.
- `apps/web/Frontend/tests/segmentationStrategies.test.mjs`: adaptación de una
  aserción de markup y cinco pruebas nuevas; se conservan aserciones funcionales.
- Este documento.

## Validaciones

Ejecutadas desde `apps/web/Frontend` con Node **24.17.0**:

| Comando | Resultado |
| --- | --- |
| `node tests/segmentationStrategies.test.mjs` | 53 passed, 0 failed |
| `node tests/characterization21.test.mjs` | 22 passed, 0 failed |
| `npm run build` | PASS, 105 módulos; sin advertencias de build |
| `git diff --check` | PASS |

La suite de segmentación cubre editor, revisiones, effective, estrategias,
selección, navegación, capas, BLOOD y regresiones 18Q-A/18Q-B. La nueva cobertura
comprueba VALIDADA consolidada, borrador distinto de effective, origen manual,
selección disponible ante error de historial y eventos del panel. La regresión
de Characterization cubre presentación 2.1 y fallbacks históricos; no se ejecutó
Characterization sobre datos reales.

## Revisión visual pendiente

No se realizó inspección en navegador automatizado. El render SSR y el host Vue
de pruebas verifican contenido/eventos, no distribución en píxeles.

Revisar manualmente en desktop y laptop estrecha:

- VALIDADA: número, fecha y origen visibles sin tarjetas repetidas.
- BORRADOR: número mostrado distinto del efectivo; Continuar edición accesible.
- MANUAL: etiqueta correcta y ausencia de método automático inventado.
- AUTOMATIC: método persistido y selección histórica conservados.
- Ausencia de overflow, botones cortados o solapamiento.
- Visor/capas de 18Q-A y ausencia de placeholders de 18Q-B.

Estado: **SPRINT 18Q-C = READY_FOR_VISUAL_REVIEW**.


## Pulido final 18Q-C.1

Se retira la línea `Resultado mostrado = resultado efectivo` cuando ambos
coinciden. Durante edición se mantienen el borrador mostrado y el resultado
efectivo por separado, con `BORRADOR · No efectivo`.

Resultado actual conserva ID, COMPLETADO, revisión, estado, fechas, tipo y
origen/método persistido. Se sustituye el conteo bruto por `Tipo: SALIVA` o
`Tipo: SANGRE`, sin modificar datos ni cálculos. El resumen de conteo existente
permanece intacto. La información de otra última ejecución, si existe en este
bloque, también muestra tipo sin repetir conteos.

En lectura se simplifica `Origen de la base: Anotación manual` a
`Origen: Anotación manual`. Durante edición se conserva la precisión
`Origen de la base`, porque un borrador puede tener objetos de origen mixto.

Historial y panel de ejecución no se modifican. Sin cambios de backend, API,
modelos, endpoints ni reglas de effective. Archivos del pulido: el panel, sus
aserciones de presentación y este documento.

Validaciones repetidas con Node 24.17.0: segmentación **53 passed**,
Characterization **22 passed**, `npm run build` **PASS** y `git diff --check`
**PASS**. Revisión visual en navegador pendiente. Sin commit ni push.

**SPRINT 18Q-C.1 = READY_FOR_VISUAL_REVIEW**
