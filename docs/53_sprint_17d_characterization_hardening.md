# Sprint 17D - Hardening de Caracterizacion

## Fecha

2026-08-31

## Commits base verificados

Antes de iniciar Sprint 17D se verifico que el working tree estaba limpio y que
existian los commits requeridos:

- `828c65f Add characterization frontend workflow`
- `f2b70e1 Update SICAM development startup guide`

Commit base de trabajo:

```text
f2b70e1
```

## Objetivo

Endurecer el flujo de `Caracterizacion` y su interaccion con `Segmentacion`
frente a errores HTTP, cambios rapidos de contexto, refresh/F5, resultados
historicos, estados vacios y navegacion con cambios locales sin guardar.

No se modificaron backend, endpoints, modelos, contratos cientificos,
microservicios ni algoritmos.

## Session storage

Se agrego persistencia de contexto minimo con `sessionStorage`, usando una sola
clave versionada:

```text
sicam.uiContext.v1
```

Esquema persistido:

```json
{
  "version": 1,
  "activeTab": "segmentacion",
  "patientId": 1,
  "caseId": 1,
  "sampleType": "SALIVA",
  "sampleId": 1,
  "segmentationResultId": 1
}
```

No se usa `localStorage`.

## Datos no persistidos

La persistencia de UI no guarda datos cientificos ni clinicos completos.

Quedan explicitamente fuera de `sessionStorage`:

- nombres de paciente;
- filenames;
- objetos segmentados;
- geometrias;
- overlays;
- caracterizaciones;
- metricas;
- revisiones completas;
- `BORRADOR`;
- `VALIDADA`;
- stacks de undo/redo;
- credenciales o tokens.

## Rehidratacion jerarquica

La restauracion no confia ciegamente en los valores persistidos.

`App.vue` solo rehidrata IDs y contexto minimo. Despues cada nivel se valida
contra datos reales cargados desde Django:

1. `SideBar.vue` valida `patientId` contra `GET /api/pacientes/`.
2. `SideBar.vue` valida `caseId` contra `GET /api/casos/` y su relacion con el
   paciente.
3. `MainContent.vue` y `CaracterizacionView.vue` validan `sampleId` contra las
   muestras disponibles del caso y `sampleType`.
4. `MainContent.vue` y `CaracterizacionView.vue` validan
   `segmentationResultId` contra los `ResultadoSegmentacion` de la muestra y
   solo restauran resultados `COMPLETADO`.

Si un nivel no existe o ya no pertenece al contexto, se limpia ese nivel y sus
descendientes. Un `ResultadoSegmentacion` con `estado = "ERROR"` no se restaura
como seleccion activa.

## Pestana activa

`activeTab` se restaura desde `sessionStorage` cuando tiene un valor valido:

- `segmentacion`
- `caracterizacion`
- `analisis`
- `registro`

Si el contexto requerido para una pestana ya no existe, la vista muestra su
estado vacio normal sin inventar seleccion.

## JSON corrupto o version desconocida

Si el valor de `sicam.uiContext.v1` no puede parsearse o tiene una version no
soportada, se elimina del `sessionStorage` y la aplicacion inicia con el contexto
por defecto.

## Dirty guard

Se centralizo en `App.vue` la confirmacion para cambios de contexto que nacen en
la aplicacion global:

- cambio de pestana;
- cambio de paciente;
- cambio de caso;
- cambio de `sampleType`.

`SideBar.vue` ya no cambia paciente/caso localmente antes de pedir el cambio al
padre. Primero emite la solicitud y `App.vue` confirma si existe trabajo local
sin guardar en `Segmentacion`.

Si el usuario cancela, permanecen intactos:

- paciente;
- caso;
- muestra;
- `ResultadoSegmentacion`;
- editor.

Los cambios internos de muestra y `ResultadoSegmentacion` siguen protegidos por
`MainContent.vue`, porque ocurren dentro del contexto directo del editor.

## Beforeunload

La proteccion existente de `beforeunload` en `MainContent.vue` se mantiene para
F5, `Ctrl+R`, cierre de pestana o cierre de ventana cuando:

```text
hasPendingDraftWork === true
```

No se dispara solo por existir un `BORRADOR` guardado. Un `BORRADOR` persistido
en backend no equivale a cambios locales pendientes.

No se persisten `workingObjects`, undo ni redo.

## Errores HTTP

`CaracterizacionView.vue` ahora usa un helper local para mostrar errores
controlados a partir de:

- `error.response.data.error`;
- `error.response.data.detail`;
- `error.response.data.message`;
- HTTP status;
- mensaje fallback.

No se exponen stack traces en UI.

## Request guards

Se mantienen los guards existentes:

- `contextRequestId`
- `resultsRequestId`
- `characterizationsRequestId`

Las respuestas tardias de contexto, resultados o caracterizaciones se descartan
si ya no corresponden al contexto activo.

Los estados dependientes se limpian al iniciar cambios validos de contexto para
evitar datos stale.

## Estados vacios

Se conserva cobertura UI para:

- sin paciente/caso;
- sin muestras;
- sin `ResultadoSegmentacion` `COMPLETADO`;
- solo resultados `ERROR`;
- sin caracterizacion vigente;
- caracterizacion stale;
- caracterizacion vigente.

## SALIVA / BLOOD

No se cambiaron reglas cientificas.

La UI mantiene:

- `SALIVA`: `membrana`, `nucleo`, `micronucleo`, indice de genotoxicidad cuando
  el backend lo entrega y citotoxicidad no disponible.
- `BLOOD`: `membrana`, `micronucleo`, sin introducir metricas de saliva.

## Responsive

No se detecto una necesidad de rediseno adicional en este sprint. Se conservan
las reglas de Sprint 12/17C:

- galeria con scroll interno;
- paneles con `min-width: 0`;
- layout compacto para rangos laptop/desktop.

La validacion responsive queda como checklist manual porque el proyecto no tiene
framework de pruebas visuales automatizadas.

## Regresion esperada

`Segmentacion` debe conservar:

- seleccion de muestra;
- seleccion de `ResultadoSegmentacion`;
- overlay;
- resultado efectivo;
- edicion;
- `BORRADOR`;
- `VALIDADA`;
- dirty guard;
- resultados historicos.

`Registro` no fue modificado.

## Validaciones automaticas

```powershell
npm.cmd run build
```

Resultado:

```text
PASS
```

La ejecucion dentro del sandbox fallo por el problema conocido de Vite/esbuild
con acceso denegado al resolver `vite.config.js`. Se repitio fuera del sandbox y
finalizo correctamente.

Advertencia no bloqueante observada fuera del sandbox:

```text
No se puede cargar profile.ps1 porque la ejecucion de scripts esta deshabilitada.
```

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
```

Resultado:

```text
PASS
System check identified no issues (0 silenced).
```

```powershell
git diff --check
```

Resultado:

```text
PASS
```

## Checklist manual

### F5 en Caracterizacion

1. Entrar a `Caracterizacion`.
2. Seleccionar paciente, caso, `SALIVA`, muestra y `ResultadoSegmentacion`.
3. Presionar F5.
4. Confirmar que se restaura el mismo contexto si sigue siendo valido.

### F5 en Segmentacion

1. Entrar a `Segmentacion`.
2. Seleccionar la misma cadena de contexto.
3. Presionar F5.
4. Confirmar que se restaura muestra y `ResultadoSegmentacion`.

### Cambios locales sin guardar

1. Entrar a modo edicion.
2. Modificar geometria sin guardar.
3. Presionar F5.
4. Confirmar advertencia estandar del navegador.
5. Cancelar y confirmar que la edicion sigue disponible.
6. Aceptar reload y confirmar que solo se recupera estado persistido en backend.

### BORRADOR guardado

1. Guardar `BORRADOR`.
2. Presionar F5.
3. Confirmar que no aparece advertencia por dirty local.
4. Confirmar que el `BORRADOR` se recupera desde backend segun las reglas
   normales.

### Contexto invalido

1. Modificar manualmente `sessionStorage.sicam.uiContext.v1` con `sampleId` o
   `segmentationResultId` invalido.
2. Recargar.
3. Confirmar fallback seguro sin excepciones y sin cruzar datos.

### Regresiones

- Cambiar de paciente con edicion local pendiente y cancelar.
- Cambiar de caso con edicion local pendiente y cancelar.
- Cambiar de `sampleType` con edicion local pendiente y cancelar.
- Cambiar de muestra y confirmar el guard existente.
- Cambiar de `ResultadoSegmentacion` y confirmar el guard existente.
- Confirmar `SALIVA` y `BLOOD` en `Caracterizacion`.
- Confirmar que `Registro` abre sin regresiones.

## Limitaciones

- No hay persistencia profunda de estado editorial local.
- No se guarda ni restaura undo/redo.
- La rehidratacion completa depende de que los componentes carguen datos reales
  desde Django.
- No existe suite automatizada frontend; la cobertura visual y de F5 requiere
  validacion manual.
