# Sprint 17C - Modulo de Caracterizacion en pestana propia

## Fecha

2026-08-29 09:07:17 -06:00

## Referencia Git

- Rama: `master`
- Commit base: `b3a29ba`

## Objetivo

Implementar una primera pantalla operativa de Caracterizacion como modulo
independiente dentro del frontend Vue/Vite, consumiendo exclusivamente la API de
Django REST.

## Alcance implementado

La pestana `Caracterizacion` dejo de ser un placeholder y ahora permite:

- reutilizar el contexto global de paciente y caso;
- alternar entre tipos de muestra `SALIVA` y `SANGRE` usando
  `segmentationTypes.js`;
- listar muestras del caso seleccionado;
- seleccionar una muestra;
- consultar resultados de segmentacion historicos de esa muestra;
- elegir explicitamente un resultado con `estado = "COMPLETADO"`;
- consultar caracterizaciones asociadas al resultado;
- mostrar la caracterizacion vigente indicada por el backend mediante
  `vigente = true`;
- solicitar caracterizacion con
  `POST /api/resultados-segmentacion/{id}/caracterizar/`;
- distinguir entre caracterizacion creada y caracterizacion vigente reutilizada.
- conservar la muestra seleccionada al pasar de `Segmentacion` a
  `Caracterizacion`;
- mantener la lista de muestras de `Caracterizacion` dentro de una zona con
  scroll interno.

No se agrego diagnostico clinico, analisis agregado por caso, exportacion,
edicion de overlay ni nuevas metricas cientificas.

## Archivos modificados

- `apps/web/Frontend/src/App.vue`
- `apps/web/Frontend/src/components/SideBar.vue`

## Archivos creados

- `apps/web/Frontend/src/services/characterizationService.js`
- `apps/web/Frontend/src/views/CaracterizacionView.vue`
- `apps/web/Frontend/src/components/characterization/CharacterizationResultPanel.vue`
- `docs/52_sprint_17c_characterization_frontend.md`

## Servicio frontend

Se creo `characterizationService.js` con funciones acotadas a Django REST:

- `obtenerCaracterizaciones(resultadoSegmentacionId)`
- `caracterizarResultado(resultadoSegmentacionId)`

No se llama directamente a microservicios FastAPI desde el frontend.

## Vista de Caracterizacion

`CaracterizacionView.vue` concentra la carga de datos operativos:

- consulta `GET /api/analisis/`;
- consulta muestras de sangre mediante `listarMuestras(SAMPLE_TYPES.BLOOD)`;
- reutiliza muestras de saliva incluidas en el analisis actual;
- consulta resultados con `obtenerResultadosSegmentacion(muestraId, sampleType)`;
- filtra resultados caracterizables por `estado = "COMPLETADO"`;
- consulta caracterizaciones con
  `GET /api/resultados-segmentacion/{id}/caracterizaciones/`;
- ejecuta caracterizacion con
  `POST /api/resultados-segmentacion/{id}/caracterizar/`.

La vista protege respuestas tardias con identificadores internos de solicitud
para contexto, resultados y caracterizaciones.

## Panel de resultado

`CharacterizationResultPanel.vue` muestra una representacion compacta:

- fuente del resultado efectivo;
- tipo de muestra;
- version del algoritmo;
- numero de caracterizaciones historicas;
- conteos por etiqueta segun `segmentationTypes.js`;
- indice de genotoxicidad para `SALIVA` cuando es calculable;
- citotoxicidad como no disponible;
- advertencias devueltas por el backend.

Para `SANGRE` se muestran conteos y se evita inventar indices cientificos.

## Contrato usado

La pantalla usa como resultado oficial solamente la caracterizacion que el
backend marca con:

```json
{
  "vigente": true
}
```

Si existen caracterizaciones pero ninguna es vigente, la UI muestra
`Caracterizacion desactualizada` y ofrece `Actualizar caracterizacion`.

Si no existe caracterizacion vigente ni historica, muestra
`Sin caracterizacion vigente` y ofrece `Caracterizar`.

Si no hay resultado de segmentacion completado, muestra:

```text
No hay una segmentacion completada disponible para caracterizar.
Primero segmenta la muestra.
```

## Contexto entre pestanas

`App.vue` conserva paciente, caso, tipo de muestra y muestra seleccionada al
cambiar entre:

- `Segmentacion`
- `Caracterizacion`

El `SideBar` se comparte entre ambas pestanas para mantener la seleccion visual
cuando se navega entre estos modulos.

La muestra se comparte como identidad minima:

```text
sampleType
sampleId
```

No se comparte el objeto Vue completo para evitar referencias obsoletas entre
vistas. Cada modulo resuelve la muestra desde su propia coleccion cargada.

Identidad canonica:

| Tipo | Identidad tecnica |
|---|---|
| `SALIVA` | `MuestraSaliva.id_muestra` |
| `SANGRE` | `MuestraSangre.id_muestra` |

No se usa `ResultadoSegmentacion.id`, indice de galeria, filename ni numero
visual como identidad tecnica compartida.

La causa del fallo inicial de continuidad fue que `CaracterizacionView.vue`
intentaba restaurar la muestra antes de tener la coleccion cargada y emitia
`sampleId=null`, lo que borraba `selectedSampleRef` en `App.vue`. La correccion
mantiene el estado global intacto cuando la muestra aun no puede resolverse.

`CaracterizacionView.vue` solo restaura la muestra si:

- pertenece al `sampleType` activo;
- pertenece al caso actual a traves del `AnalisisPred` cargado;
- sigue existiendo en la coleccion disponible.

Si la muestra ya no pertenece al contexto actual, la seleccion queda vacia y no
se hace fallback silencioso a la primera muestra.

El flujo `Segmentacion -> Caracterizacion` preserva la muestra seleccionada. El
flujo inverso `Caracterizacion -> Segmentacion` tambien comparte `sampleId`
cuando el tipo de muestra coincide y `MainContent.vue` puede resolver esa
muestra en su galeria.

Cuando `Caracterizacion` restaura una muestra valida, intenta llevar el item
seleccionado a la zona visible mediante `scrollIntoView({ block: "nearest" })`.

## Identificacion visual de muestras

La identificacion visual se unifico entre `Segmentacion` y `Caracterizacion`:

- identificador principal: filename de la imagen;
- identificador secundario: `Muestra #id_muestra`.

El PK sigue siendo identidad tecnica, pero no es el unico texto visible. Esto
permite reconocer la misma imagen al cambiar de modulo.

## Galeria de Caracterizacion

La lista `Muestras de Saliva/Sangre` mantiene su header fuera del area
scrollable:

```text
Muestras de Saliva    N
Muestras de Sangre    N
```

La lista vertical conserva thumbnails, nombre de archivo y estado seleccionado,
pero ahora usa scroll interno para que muchas muestras no alarguen toda la
pagina.

Estrategia CSS:

- `samples-panel` usa `max-height: calc(100vh - 176px)`;
- `sample-list` usa `flex: 1 1 auto`, `min-height: 0` y `overflow-y: auto`;
- en viewport estrecho se limita con `max-height: min(360px, calc(100vh - 220px))`.

No se implemento paginacion, infinite scroll, virtual list ni rediseño de items.

## Segmentacion a caracterizar

La etiqueta visible del selector cambio de `Resultado de segmentacion` a
`Segmentacion a caracterizar` para aclarar que la caracterizacion se calcula
sobre un `ResultadoSegmentacion` explicito.

Comportamiento:

- 0 resultados `COMPLETADO`: no se muestra un select vacio; se muestra
  `No hay una segmentacion completada disponible para caracterizar` y la accion
  queda deshabilitada.
- 1 resultado `COMPLETADO`: no se muestra select; se muestra una tarjeta estatica
  con fecha/hora y `Resultado #id`.
- 2 o mas resultados `COMPLETADO`: se muestra select con fecha/hora y
  `Resultado #id`.

Los resultados `ERROR` quedan excluidos de la seleccion caracterizable.

El default se calcula ordenando resultados completados por `creado_en`
descendente y, como desempate, `id` descendente. La seleccion sigue siendo de
`ResultadoSegmentacion`; el backend resuelve si usa fuente `AUTOMATICO` o
revision `VALIDADA`.

## Seleccion compartida de ResultadoSegmentacion

Sprint 17C.3 agrega una identidad compartida adicional entre `Segmentacion` y
`Caracterizacion`:

```text
selectedSegmentationResultId
```

Esta identidad corresponde al PK de `ResultadoSegmentacion` y solo es valida
dentro del contexto:

```text
sampleType
sampleId
```

La muestra y el resultado no representan el mismo concepto:

| Concepto | Identidad | Funcion |
|---|---|---|
| Muestra | `sampleType` + `Muestra.id_muestra` | Imagen o muestra biologica seleccionada. |
| ResultadoSegmentacion | `ResultadoSegmentacion.id` | Ejecucion automatica historica asociada a una muestra. |

`App.vue` conserva solo identidades minimas, no objetos Vue completos. Si cambia
paciente, caso, `sampleType` o `sampleId`, la seleccion de
`ResultadoSegmentacion` se invalida para evitar mostrar un resultado que
pertenezca a otra muestra.

## Segmentacion seleccionada

La pestana `Segmentacion` ya no usa implicitamente siempre el primer elemento del
historial como resultado activo. Ahora resuelve el resultado activo asi:

1. Si `selectedSegmentationResultId` pertenece a la muestra actual y esta en
   `estado = "COMPLETADO"`, se usa ese resultado.
2. Si no existe seleccion compartida valida, se usa el resultado `COMPLETADO`
   mas reciente.
3. Los resultados `ERROR` quedan fuera del selector activo, aunque pueden seguir
   apareciendo en historial.

El selector visible usa la terminologia:

```text
Segmentacion seleccionada
```

Comportamiento 0/1/N en `Segmentacion`:

- 0 resultados `COMPLETADO`: se muestra `Sin segmentaciones completadas` y la
  accion de ejecutar segmentacion sigue disponible.
- 1 resultado `COMPLETADO`: no se muestra select; se muestra una tarjeta
  estatica con fecha/hora y `Resultado #id`.
- 2 o mas resultados `COMPLETADO`: se muestra select ordenado por `creado_en`
  descendente e `id` descendente como desempate.

Cambiar el resultado seleccionado en `Segmentacion` actualiza:

- resultado efectivo mostrado;
- overlay SVG;
- resumen de conteo;
- estado de `RevisionSegmentacion`;
- indicador de `BORRADOR`;
- revision `VALIDADA` vigente para ese resultado;
- contexto del editor.

La fuente efectiva sigue resolviendose por resultado:

```text
VALIDADA si existe
AUTOMATICO si no existe VALIDADA
```

No se agrego selector `AUTOMATICO`/`VALIDADA`.

Si se ejecuta una nueva segmentacion y Django crea un nuevo
`ResultadoSegmentacion`, la UI selecciona automaticamente ese nuevo resultado.
Los resultados historicos anteriores permanecen disponibles.

## Continuidad Segmentacion / Caracterizacion

La seleccion de `ResultadoSegmentacion` se comparte en ambas direcciones:

- `Segmentacion -> Caracterizacion`: si el usuario inspecciona `Resultado #15`,
  `Caracterizacion` restaura `Resultado #15` como `Segmentacion a caracterizar`
  cuando pertenece a la muestra actual.
- `Caracterizacion -> Segmentacion`: si el usuario elige `Resultado #10`, al
  volver a `Segmentacion` se restaura `Resultado #10` si continua valido.

`Caracterizacion` mantiene su UX 0/1/N:

- 0 resultados `COMPLETADO`: no hay caracterizacion disponible.
- 1 resultado `COMPLETADO`: tarjeta estatica.
- 2 o mas resultados `COMPLETADO`: select `Segmentacion a caracterizar`.

La lista de caracterizaciones se carga siempre para el
`ResultadoSegmentacion.id` seleccionado, no para el resultado mas reciente salvo
que ese sea el default valido.

## Aislamiento por resultado

`RevisionSegmentacion` y `ResultadoCaracterizacion` quedan asociados al
`ResultadoSegmentacion` seleccionado:

- un `BORRADOR` de `Resultado #10` no se mezcla con un `BORRADOR` de
  `Resultado #15`;
- una revision `VALIDADA` de `Resultado #10` no se muestra como fuente efectiva
  de `Resultado #15`;
- editar un resultado historico crea o reutiliza el `BORRADOR` de ese resultado,
  sin saltar automaticamente al resultado mas reciente.

Las cargas asincronas de resultado efectivo, revisiones y caracterizaciones
siguen usando guards por ID para evitar que una respuesta tardia sobrescriba la
seleccion actual.

## Proteccion de BORRADOR pendiente

El cambio de pestana desde `Segmentacion` consulta el estado expuesto por
`MainContent.vue`:

- `hasPendingDraftWork`
- `confirmDiscardDraftChanges()`

Si hay trabajo local pendiente, se solicita confirmacion antes de abandonar el
modulo de segmentacion.

## Validaciones ejecutadas

### Frontend

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

La primera ejecucion dentro del sandbox fallo por el problema conocido de
Vite/esbuild con acceso denegado al resolver `vite.config.js`. Se repitio fuera
del sandbox y finalizo correctamente.

Advertencia observada fuera del sandbox:

```text
No se puede cargar profile.ps1 porque la ejecucion de scripts esta deshabilitada.
```

No bloqueo el build.

### Backend

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
```

Resultado:

```text
System check identified no issues (0 silenced).
```

### Revision de diff

```powershell
git diff --check
```

Resultado:

```text
PASS
```

## Checklist manual

- Seleccionar un paciente y caso desde el `SideBar`.
- Entrar a `Caracterizacion`.
- Confirmar que el paciente y caso se conservan.
- Confirmar que la muestra seleccionada en `Segmentacion` se conserva al entrar
  a `Caracterizacion`.
- Confirmar que una lista con muchas muestras usa scroll interno y no alarga la
  pagina completa.
- Confirmar que el mismo filename y `Muestra #id` aparecen en ambos modulos.
- Cambiar entre `Saliva` y `Sangre`.
- Seleccionar una muestra con resultado de segmentacion completado.
- Confirmar UX de 0, 1 y multiples resultados `COMPLETADO`.
- Confirmar que resultados `ERROR` no aparecen como caracterizables.
- Pulsar `Caracterizar`.
- Confirmar que aparece una caracterizacion vigente.
- Repetir `Caracterizar` y confirmar que reutiliza la vigente.
- Validar que `SALIVA` muestra conteos e indice de genotoxicidad cuando aplica.
- Validar que `SANGRE` muestra conteos sin inventar indices.
- Confirmar que una muestra sin segmentacion completada deshabilita la accion.
- Confirmar que cambiar de resultado recarga sus caracterizaciones.
- Confirmar que al salir de `Segmentacion` con BORRADOR local aparece
  confirmacion antes de cambiar de modulo.

## Limitaciones

- No se muestra diagnostico clinico.
- No hay resumen agregado por caso.
- No hay exportacion CSV/PDF.
- La continuidad de muestra depende de que el `sampleId` exista en la coleccion
  cargada del modulo destino.
- No existe framework de pruebas frontend automatizadas en el proyecto.

## Siguiente paso recomendado

Validar manualmente el flujo con datos reales de saliva y sangre. Despues,
planear un sprint separado para resumen agregado por caso o exportacion, si se
requiere para operacion.
