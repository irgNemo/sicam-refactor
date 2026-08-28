# Sprint 17B - Nucleo de caracterizacion sobre ResultadoSegmentacion efectivo

## Fecha

2026-08-27 18:17:21 -06:00

## Proposito

Este sprint agrega un nucleo backend minimo para caracterizar resultados de
segmentacion ya persistidos, consumiendo siempre el resultado efectivo:

```text
ResultadoSegmentacion
-> resolve_effective_segmentation()
-> latest VALIDADA si existe
-> AUTOMATICO si no existe VALIDADA
-> caracterizador puro
-> ResultadoCaracterizacion inmutable
```

No se modifica `ResultadoAnalisis`, no se modifica frontend, no se modifican
microservicios y no se ejecutan algoritmos de segmentacion.

## Regla oficial de fuente efectiva

La caracterizacion oficial nunca consume `BORRADOR`.

- Si existe una `RevisionSegmentacion` `VALIDADA`, se usa la ultima validada
  por `numero_revision`.
- Si no existe `VALIDADA`, se usa `ResultadoSegmentacion.resultado_normalizado`.
- Los objetos manuales y automaticos cuentan igual.
- `ResultadoSegmentacion.respuesta_json` y
  `ResultadoSegmentacion.resultado_normalizado` permanecen intactos.

## Evidencia cientifica usada

La auditoria de Sprint 17A encontro en el legacy SALIVA:

- conteos de citoplasmas/membranas;
- conteos de nucleos;
- conteos de micronucleos;
- conteos de celulas binucleadas y trinucleadas;
- `cytotoxicity_index = (binucleate + trinucleate) / cytoplasm`;
- `genotoxicity_index = micronucleus / cytoplasm`.

En el contrato normalizado actual no existe la relacion reproducible
citoplasma-nucleo-micronucleo que el legacy calculaba durante segmentacion con
recortes y mascaras. Por eso, Sprint 17B no implementa binucleadas,
trinucleadas ni citotoxicidad.

Los filtros de area, elipse, color HSV, jerarquia de contornos y DBSCAN se
clasifican como segmentacion/postprocesamiento, no como caracterizacion nueva.
No se reejecutan desde Django.

## Funciones puras creadas

Se agrego el paquete:

```text
apps/web/Backend/api/services/characterization/
```

Archivos:

- `geometry.py`: primitivas puras `polygon_area()` y `polygon_perimeter()`.
- `saliva.py`: caracterizador puro para SALIVA.
- `service.py`: orquestacion ORM y resolucion efectiva.
- `types.py`: version y constantes del contrato.
- `__init__.py`: exportaciones del paquete.

Las funciones puras no realizan consultas ORM y no modifican sus entradas.

## Contrato de salida

Version inicial:

```text
algorithm_version = "1.0"
resultado_json.version = "1.0"
```

Estructura general:

```json
{
  "version": "1.0",
  "sample_type": "SALIVA",
  "source": {
    "type": "AUTOMATICO",
    "resultado_segmentacion_id": 1,
    "revision_segmentacion_id": null,
    "numero_revision": null
  },
  "counts": {
    "membrana": 2,
    "nucleo": 1,
    "micronucleo": 1
  },
  "indices": {
    "genotoxicity_index": 0.5,
    "cytotoxicity_index": null
  },
  "characterization_capabilities": {
    "counts": "AVAILABLE",
    "genotoxicity_index": "AVAILABLE",
    "binucleate_trinucleate": "BLOCKED_SCIENTIFIC_RULE",
    "cytotoxicity_index": "BLOCKED_SCIENTIFIC_RULE"
  },
  "blocked": [
    {
      "code": "BLOCKED_SCIENTIFIC_RULE",
      "metric": "binucleate_trinucleate"
    },
    {
      "code": "BLOCKED_SCIENTIFIC_RULE",
      "metric": "cytotoxicity_index"
    }
  ],
  "warnings": [
    "La regla legacy de asociacion citoplasma-nucleo-micronucleo depende de recortes y mascaras de segmentacion que no estan disponibles en el contrato normalizado actual."
  ]
}
```

## SALIVA

Implementado:

- conteo de `membrana`;
- conteo de `nucleo`;
- conteo de `micronucleo`;
- `genotoxicity_index = micronucleo / membrana`;
- si `membrana = 0`, `genotoxicity_index = null`.

Bloqueado por regla cientifica:

- celulas binucleadas;
- celulas trinucleadas;
- `cytotoxicity_index`.

Motivo:

```text
BLOCKED_SCIENTIFIC_RULE
```

La regla legacy dependia de asociacion espacial por recortes y mascaras
producidas durante segmentacion, no de los poligonos normalizados actuales.

## SANGRE

Sprint 17B no inventa caracterizacion cientifica para `SANGRE`.

Implementado:

- conteo de `membrana`;
- conteo de `micronucleo`.

No implementado:

- `genotoxicity_index`;
- `cytotoxicity_index`;
- cualquier indice biologico no demostrado en el legacy de sangre.

La salida marca estas capacidades como `NOT_DEFINED` y documenta que SANGRE
queda en modo counts-only.

## Persistencia

Modelo nuevo:

```text
ResultadoCaracterizacion
```

Campos:

- `id_resultado_caracterizacion`;
- `resultado_segmentacion`;
- `revision_segmentacion`, nullable;
- `source_type`;
- `sample_type`;
- `algorithm_version`;
- `resultado_json`;
- `created_at`.

La migracion creada es:

```text
apps/web/Backend/api/migrations/0006_resultadocaracterizacion_and_more.py
```

Constraint agregado:

- `resultado_caracterizacion_source_consistency`;
- `AUTOMATICO` requiere `revision_segmentacion = null`;
- `VALIDADA` requiere `revision_segmentacion != null`.

No se elimina ni se reemplaza `ResultadoAnalisis`.

## Trazabilidad y vigencia

Cada caracterizacion es un snapshot inmutable. No se eliminan caracterizaciones
anteriores y no hay signals ni triggers automaticos.

La vigencia se calcula con:

```text
is_characterization_current()
```

Criterio:

- misma `algorithm_version`;
- mismo `source_type` que el resultado efectivo actual;
- si la fuente es `AUTOMATICO`, no debe apuntar a revision;
- si la fuente es `VALIDADA`, debe apuntar a la revision efectiva actual.

Por lo tanto, una caracterizacion automatica se vuelve stale si luego aparece
una revision `VALIDADA`.

## API agregada

Endpoints bajo `ResultadoSegmentacionViewSet`:

```text
POST /api/resultados-segmentacion/{id}/caracterizar/
GET  /api/resultados-segmentacion/{id}/caracterizaciones/
```

`POST caracterizar`:

- resuelve el resultado efectivo;
- crea un `ResultadoCaracterizacion`;
- devuelve el serializer del snapshot creado.

`GET caracterizaciones`:

- devuelve lista ordenada por `created_at` descendente;
- incluye `vigente` por cada snapshot.

## Pruebas agregadas

Se agregaron pruebas en:

```text
apps/web/Backend/api/tests.py
```

Cobertura:

- primitivas puras de area y perimetro;
- caracterizacion SALIVA desde automatico;
- caracterizacion SALIVA desde latest `VALIDADA`;
- `BORRADOR` ignorado;
- objetos manuales y automaticos cuentan igual;
- `genotoxicity_index` con divisor cero devuelve `null`;
- BLOOD/SANGRE devuelve solo conteos;
- `ResultadoSegmentacion` original no se modifica;
- snapshots stale/current;
- `POST caracterizar`;
- `GET caracterizaciones`;
- validacion de resultado efectivo invalido.

## Diferencias frente al legacy

Preservado:

- conteos por etiqueta;
- razon `micronucleo / membrana` para SALIVA;
- no multiplicar por 100.

No preservado en este sprint:

- binucleadas;
- trinucleadas;
- citotoxicidad;
- asociacion espacial por citoplasma.

Estas diferencias quedan documentadas como bloqueo cientifico, no como deuda
tecnica ordinaria.

## Limitaciones

- No hay endpoint agregado al frontend.
- No hay generacion de reportes CSV/PDF.
- No hay backfill de caracterizaciones historicas.
- No se calcula caracterizacion cientifica de sangre.
- No se recupera asociacion celula-nucleo-micronucleo desde mascaras legacy.

## Pendientes para Sprint 17C

- Exponer la caracterizacion en frontend o preparar reportes, segun prioridad.
- Definir con experto si se debe reconstruir asociacion espacial para
  binucleadas/trinucleadas/citotoxicidad.
- Decidir si caracterizacion debe ejecutarse manualmente desde UI o por flujo
  operativo controlado.
- Evaluar estrategia de backfill solo si se requiere para datos historicos.

## Verificacion Sprint 17B-V

Fecha local de verificacion:

```text
2026-08-28
```

### Equivalencia cytoplasm -> membrana

Clasificacion:

```text
PROBADO 1:1
```

Evidencia:

- En el legacy SALIVA,
  `apps/segmentation-saliva/segmentacion_core/controller/controllerroot.py`
  construye el modelo de membranas con `membranas_500_125` y `diameter = 125`
  en las lineas 652-659.
- Ese resultado `masks[i]` se asigna directamente como
  `image.mask_cytoplasm = Mask(..., Mask.CYTOPLASM)` en la linea 665.
- `Mask.add_elements()` crea objetos `Cytoplasm` cuando
  `self.type == Mask.CYTOPLASM` en
  `apps/segmentation-saliva/segmentacion_core/model/mask.py` lineas
  153-164.
- En el microservicio SALIVA actual,
  `apps/segmentation-saliva/app/services/segmentador.py` devuelve
  `"membranas": masks_mem.astype(np.uint16)` en las lineas 43 y 49-52.
- El endpoint `apps/segmentation-saliva/app/routers/segmentacion.py`
  convierte `resultado["membranas"]` a JSON con
  `obtener_poligonos_desde_mascara(..., "membrana")` en la linea 18.
- `apps/segmentation-saliva/app/utils/poligonos.py` conserva ese tipo como
  `"tipo": tipo_objeto` en las lineas 44-47.
- El normalizador Django
  `apps/web/Backend/api/services/segmentation/normalizers.py` mapea
  `raw_object.get("tipo")` a `label` en la linea 56.

Conclusion:

```text
objeto legacy Cytoplasm
-> Mask.CYTOPLASM derivado de la mascara de membranas
-> JSON tipo="membrana"
-> resultado_normalizado.objects[].label = "membrana"
```

Por lo tanto, en el contexto SALIVA actual, `membrana` es el nombre canonico
de API para el objeto celular/cytoplasm legacy.

### Decision sobre genotoxicity_index

La equivalencia anterior valida mantener:

```text
genotoxicity_index = micronucleo / membrana
```

Esta razon corresponde al legacy:

```text
genotoxicity_index = micronucleus / cytoplasm
```

No se multiplica por 100. Si `membrana = 0`, el valor se conserva como
`null`.

### Cytotoxicity

`cytotoxicity_index` sigue como:

```text
BLOCKED_SCIENTIFIC_RULE
```

Motivo:

- El legacy calcula binucleadas y trinucleadas durante la seleccion de nucleos
  por cada citoplasma.
- `apps/segmentation-saliva/segmentacion_core/model/mask.py` incrementa
  `total_binucleate` y `total_trinucleate` cuando un `Cytoplasm` tiene 2 o 3
  nucleos en las lineas 187-197.
- `apps/segmentation-saliva/segmentacion_core/model/folder.py` calcula
  `cytotoxicity_index = (binucleate + trinucleate) / cytoplasm` en la linea
  192.
- Esa asociacion citoplasma-nucleo no esta portada de forma inequivoca al
  contrato normalizado actual.

### Migracion local

Antes:

```text
[ ] 0006_resultadocaracterizacion_and_more
```

Comando ejecutado:

```powershell
python manage.py migrate
```

Resultado:

```text
Applying api.0006_resultadocaracterizacion_and_more... OK
```

Despues:

```text
[X] 0006_resultadocaracterizacion_and_more
```

### Modelo, constraint e inmutabilidad

`ResultadoCaracterizacion` contiene:

- `resultado_segmentacion`;
- `revision_segmentacion`, nullable;
- `source_type`;
- `sample_type`;
- `algorithm_version`;
- `resultado_json`;
- `created_at`.

Constraint validado:

```text
resultado_caracterizacion_source_consistency
```

Casos rechazados por BD:

- `AUTOMATICO` con `revision_segmentacion`;
- `VALIDADA` sin `revision_segmentacion`.

Riesgo residual:

```text
El constraint SQL no garantiza que revision_segmentacion pertenezca al mismo
ResultadoSegmentacion ni que sea la revision efectiva mas reciente.
```

Esa consistencia la aplica actualmente
`characterize_resultado_segmentacion()`, que usa
`resolve_effective_segmentation()`.

No existe endpoint `PATCH`/`PUT`/`DELETE` para `ResultadoCaracterizacion`.
El admin esta registrado con campos de lectura para inspeccion operativa.

### POST repetido

Comportamiento real actual:

```text
POST /api/resultados-segmentacion/{id}/caracterizar/
```

crea un nuevo snapshot cada vez, aunque no cambien:

- resultado efectivo;
- `source_type`;
- `revision_segmentacion`;
- `algorithm_version`.

Smoke sobre `ResultadoSegmentacion id=2`:

```text
before = 1
after primer POST de la serie = 2
after POST repetido = 3
```

Politica recomendada para siguiente iteracion:

```text
Si misma fuente efectiva + misma revision efectiva + misma algorithm_version
ya existe y esta vigente, reutilizarla o devolverla sin crear duplicado.
```

No se implemento esa politica en Sprint 17B-V.

### Smoke real SALIVA

Resultado automatico usado:

```text
ResultadoSegmentacion id=2
source_type=AUTOMATICO
revision_segmentacion=null
```

Counts efectivos:

```json
{
  "membrana": 30,
  "nucleo": 20,
  "micronucleo": 9
}
```

`genotoxicity_index` calculado:

```text
9 / 30 = 0.3
```

Resultado validado usado:

```text
ResultadoSegmentacion id=10
source_type=VALIDADA
revision_segmentacion=11
```

Counts desde `resultado_editado` validado:

```json
{
  "membrana": 27,
  "nucleo": 20,
  "micronucleo": 9
}
```

`genotoxicity_index` calculado:

```text
9 / 27 = 0.3333333333333333
```

### Smoke real SANGRE

Resultado automatico usado:

```text
ResultadoSegmentacion id=17
source_type=AUTOMATICO
revision_segmentacion=null
```

Counts:

```json
{
  "membrana": 350,
  "micronucleo": 1
}
```

Resultado validado usado:

```text
ResultadoSegmentacion id=16
source_type=VALIDADA
revision_segmentacion=16
```

Counts:

```json
{
  "membrana": 280,
  "micronucleo": 2
}
```

SANGRE no produjo `nucleo`, `genotoxicity_index` ni
`cytotoxicity_index`.

### GET caracterizaciones

Para los resultados usados en smoke,

```text
GET /api/resultados-segmentacion/{id}/caracterizaciones/
```

devolvio HTTP 200, lista ordenada por `created_at` descendente y campo
`vigente` en el serializer.

### Stale validado

Se agregaron pruebas automatizadas para confirmar:

- `AUTOMATICO` caracterizado queda stale cuando aparece una `VALIDADA`.
- `VALIDADA #1` caracterizada queda stale cuando aparece una `VALIDADA #2`.
- una caracterizacion queda stale si cambia
  `CHARACTERIZATION_ALGORITHM_VERSION`.

### ResultadoAnalisis

Antes y despues del smoke:

```text
ResultadoAnalisis count = 0
```

El flujo de caracterizacion no crea, no modifica y no consume
`ResultadoAnalisis`.

### Datos conservados

Se conservaron las caracterizaciones reales creadas por smoke:

- `ResultadoCaracterizacion id=1`, SALIVA automatico para resultado 2.
- `ResultadoCaracterizacion id=2`, SALIVA automatico repetido para resultado 2.
- `ResultadoCaracterizacion id=3`, SALIVA validado para resultado 10.
- `ResultadoCaracterizacion id=4`, SANGRE automatico para resultado 17.
- `ResultadoCaracterizacion id=5`, SANGRE validado para resultado 16.
- `ResultadoCaracterizacion id=6`, SALIVA automatico repetido para resultado 2.

Se elimino un registro artificial temporal creado durante una prueba manual de
constraint:

```text
ResultadoCaracterizacion id=7
```

Motivo: fue creado directamente por ORM con `resultado_json={}` y no
representaba un smoke real del endpoint.

## Hotfix Sprint 17B.1 - Idempotencia y hardening

### Characterization logical key

La identidad logica de una caracterizacion queda definida como:

Para fuente automatica:

```text
resultado_segmentacion
source_type = AUTOMATICO
revision_segmentacion = NULL
algorithm_version
```

Para fuente validada:

```text
resultado_segmentacion
source_type = VALIDADA
revision_segmentacion = revision efectiva exacta
algorithm_version
```

`sample_type` debe coincidir con `ResultadoSegmentacion.tipo_muestra`, pero no
forma parte de la key porque deriva del resultado segmentado.

### POST idempotente

`characterize_resultado_segmentacion()` delega en
`get_or_create_resultado_caracterizacion()`.

El flujo transaccional es:

```text
transaction.atomic()
-> ResultadoSegmentacion.objects.select_for_update().get(pk=...)
-> resolve_effective_segmentation()
-> construir logical key
-> buscar ResultadoCaracterizacion existente por key
-> si existe, devolver snapshot existente sin recalcular
-> si no existe, caracterizar y persistir snapshot nuevo
```

El endpoint:

```text
POST /api/resultados-segmentacion/{id}/caracterizar/
```

devuelve:

- HTTP 201 si crea un snapshot nuevo;
- HTTP 200 si reutiliza un snapshot existente.

Esto mantiene el contrato de respuesta y agrega semantica idempotente.

### Cuándo se crea un nuevo snapshot

Se crea un nuevo `ResultadoCaracterizacion` cuando cambia cualquiera de estas
condiciones:

- `ResultadoSegmentacion`;
- fuente efectiva `AUTOMATICO` -> `VALIDADA`;
- revision efectiva `VALIDADA #1` -> `VALIDADA #2`;
- `CHARACTERIZATION_ALGORITHM_VERSION`.

No se sobrescriben snapshots anteriores.

### Cross-reference validation

Se agrego validacion de aplicacion en `ResultadoCaracterizacion.clean()`:

- `AUTOMATICO` rechaza `revision_segmentacion`;
- `VALIDADA` requiere `revision_segmentacion`;
- la revision asociada debe pertenecer al mismo `ResultadoSegmentacion`;
- la revision asociada debe estar `VALIDADA`.

El service oficial ejecuta `full_clean()` antes de persistir snapshots nuevos.

### Sin unique constraint nuevo

No se agrego migracion `0007` ni constraint unique nuevo.

Decision:

```text
transaction.atomic()
+ select_for_update() del ResultadoSegmentacion padre
+ lookup por logical key
```

Motivos:

- ya existen duplicados locales generados por smoke;
- se evita una migracion innecesaria en este hotfix;
- el lock del padre serializa requests concurrentes para el mismo resultado.

### Duplicados locales

Auditoria local posterior a Sprint 17B-V:

```text
total ResultadoCaracterizacion = 6
```

Grupo duplicado exacto:

```text
key = (resultado_segmentacion=2, source_type=AUTOMATICO,
       revision_segmentacion=NULL, algorithm_version=1.0)
ids = [1, 2, 6]
resultado_json equality = [True, True, True]
```

Estos duplicados corresponden al smoke real de Sprint 17B-V y se conservaron.
No se borro informacion historica.

Con la idempotencia nueva, una llamada repetida para esa misma key reutiliza el
snapshot mas antiguo por `created_at` e `id_resultado_caracterizacion`.

### Tests Sprint 17B.1

Se agrego cobertura para:

- idempotencia del service;
- idempotencia del endpoint POST;
- no recalcular si existe snapshot vigente por la misma key;
- nueva `VALIDADA` despues de `AUTOMATICO` crea snapshot nuevo;
- `VALIDADA #2` crea snapshot nuevo y vuelve stale a `VALIDADA #1`;
- cambio de `CHARACTERIZATION_ALGORITHM_VERSION` crea snapshot nuevo;
- rechazo de revision cruzada;
- rechazo de revision `BORRADOR` con `source_type=VALIDADA`.
