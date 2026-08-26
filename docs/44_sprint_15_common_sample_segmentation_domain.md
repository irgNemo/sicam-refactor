# Sprint 15 - Dominio comun de muestras saliva/sangre y preparacion multimodal

## Proposito

Este sprint prepara el dominio de segmentacion para soportar mas de un tipo de muestra sin activar todavia un flujo end-to-end de sangre.

El objetivo fue reducir supuestos hardcodeados de saliva en la capa Django y frontend, documentar el estado real del monorepo y dejar una base explicita para que un sprint posterior agregue `MuestraSangre` o un modelo comun de muestra con una estrategia de compatibilidad.

## Alcance aplicado

Se trabajó en:

- `apps/web/Backend`
- `apps/web/Frontend`
- `docs/`

No se modificaron:

- `apps/segmentation-saliva`
- `apps/segmentation-blood`
- algoritmos de segmentacion
- `cellpose/`
- modelos Django
- migraciones
- endpoints existentes

## Auditoria del dominio actual

### Modelos Django

El backend Django sigue centrado en saliva:

- `MuestraSaliva` es el unico modelo de muestra versionado en Django.
- `ResultadoSegmentacion.muestra` es `ForeignKey` a `MuestraSaliva`.
- `ResultadoSegmentacion.tipo_muestra` existe, pero la relacion estructural sigue siendo saliva.
- `RevisionSegmentacion` apunta a `ResultadoSegmentacion`, por lo que conceptualmente puede reutilizarse para otros tipos cuando `ResultadoSegmentacion` deje de depender solo de `MuestraSaliva`.

Conclusion: `ResultadoSegmentacion` no es todavia un resultado comun real para saliva y sangre; es compatible a nivel conceptual, pero no a nivel relacional.

### Flujo actual de saliva

El flujo validado sigue siendo:

```text
MuestraSaliva
-> POST /api/muestras/{id}/segmentar/
-> segment_image("SALIVA", image_bytes, filename=...)
-> ResultadoSegmentacion
-> resultado_normalizado
-> RevisionSegmentacion
-> resultado efectivo
-> frontend overlay/editor
```

Este sprint no cambia ese flujo.

### Microservicio de sangre

El microservicio de sangre existe como componente separado en:

```text
apps/segmentation-blood
```

La entrada FastAPI observada es:

```text
apps/segmentation-blood/main.py
```

Ruta observada:

```text
POST /api/v1/segmentar
```

Payload observado:

```text
multipart/form-data
file=<UploadFile>
```

Respuesta esperada por el codigo:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20], [15, 25]]
    }
  ]
}
```

Etiquetas detectadas:

- `membrana`
- `micronucleo`

No se detecto una etiqueta equivalente a `nucleo` en el contrato observado de sangre.

## Cambios realizados

### Backend

Se creo:

```text
apps/web/Backend/api/services/segmentation/types.py
```

Este modulo centraliza:

- `SampleType.SALIVA`
- `SampleType.BLOOD`, representado como `SANGRE`
- aliases aceptados (`SALIVA`, `SANGRE`, `BLOOD`)
- configuracion de etiquetas por tipo de muestra
- soporte declarado de normalizacion y revision experta

Configuracion actual:

```text
SALIVA:
  allowed_labels:
    - membrana
    - nucleo
    - micronucleo
  supports_segmentation: true
  supports_expert_review: true

SANGRE:
  allowed_labels:
    - membrana
    - micronucleo
  supports_segmentation: true
  supports_expert_review: true
```

Actualizacion Sprint 16B: `supports_segmentation: true` en `SANGRE` significa que Django ya tiene endpoint backend para segmentar `MuestraSangre` usando el cliente de sangre. La UI de sangre queda pendiente.

Se actualizaron:

- `api/services/segmentation/factory.py`
- `api/services/segmentation/normalizers.py`
- `api/services/segmentation/revisions.py`
- `api/serializers.py`
- `api/views.py`

El normalizador conserva el contrato `version: "1.1"` y ahora usa la configuracion de tipo de muestra para aceptar `SALIVA` o `SANGRE` cuando la estructura de entrada es compatible con `objetos[].tipo` y `objetos[].puntos`.

La validacion de revisiones ahora puede aplicar etiquetas permitidas por tipo de muestra. El valor por defecto sigue siendo `SALIVA` para conservar compatibilidad.

### Frontend

Se creo:

```text
apps/web/Frontend/src/domain/segmentationTypes.js
```

Este modulo centraliza:

- tipos de muestra usados por la UI;
- etiquetas por tipo;
- nombres de presentacion;
- colores por etiqueta;
- orden de renderizado;
- etiqueta de dibujo por defecto.

Se actualizaron:

- `src/components/MainContent.vue`
- `src/components/segmentation/OverlayLayersCard.vue`
- `src/components/segmentation/SegmentationCountSummary.vue`

La UI actual sigue trabajando con resultados de saliva, pero:

- las capas visibles salen de la configuracion activa;
- el selector de tipo a dibujar sale de etiquetas editables configuradas;
- el resumen de conteo ya no depende exclusivamente de filas hardcodeadas para saliva;
- los colores por etiqueta se resuelven desde una configuracion compartida del frontend.

## Contrato preparado

### Resultado normalizado comun

La estructura comun esperada sigue siendo:

```json
{
  "version": "1.1",
  "sample_type": "SALIVA",
  "objects": [
    {
      "id": 1,
      "label": "membrana",
      "geometry": {
        "type": "polygon",
        "points": [[10, 20], [15, 25]]
      },
      "source": {
        "raw_id": 255,
        "raw_type": "membrana"
      }
    }
  ],
  "summary": {
    "total_objects": 1,
    "counts_by_label": {
      "membrana": 1
    }
  }
}
```

Para sangre, el mismo contrato puede usar:

```json
{
  "version": "1.1",
  "sample_type": "SANGRE",
  "objects": [
    {
      "id": 1,
      "label": "micronucleo",
      "geometry": {
        "type": "polygon",
        "points": [[10, 20], [15, 25]]
      },
      "source": {
        "raw_id": 255,
        "raw_type": "micronucleo"
      }
    }
  ],
  "summary": {
    "total_objects": 1,
    "counts_by_label": {
      "micronucleo": 1
    }
  }
}
```

## Pendientes para activar sangre end-to-end

Actualizacion Sprint 16A: ya existe una solucion transicional de persistencia relacional para sangre mediante `MuestraSangre` y `ResultadoSegmentacion.muestra_sangre`. `ResultadoSegmentacion.muestra` se preserva para saliva.

Actualizacion Sprint 16B: ya existe endpoint backend para segmentar `MuestraSangre`; todavia falta integracion frontend.

Antes de activar un flujo real de sangre todavia se requiere definir:

- origen de imagenes de sangre en frontend;
- filtros de galeria por tipo de muestra;
- resumen de caso combinando saliva y sangre;
- reglas de revision experta para sangre;
- estrategia de datos historicos ya guardados como `SALIVA`.

## Riesgos actuales

- `ResultadoSegmentacion` ya puede apuntar a `MuestraSaliva` o `MuestraSangre`, pero usa una estrategia transicional de dos FK y todavia no existe un modelo comun `ImagenMuestra`.
- El frontend puede renderizar configuracion para `SANGRE`, pero no tiene todavia galeria ni flujo de carga de muestras de sangre.
- El microservicio de sangre puede cargar modelos pesados al arrancar; este sprint no lo ejecuta.
- `supports_segmentation` para `SANGRE` ya esta activo a nivel de backend Django; falta integracion UI.
- Los historicos existentes no se migraron ni se recalcularon.

## Pruebas agregadas

Se agrego cobertura para:

- configuracion de etiquetas por tipo de muestra;
- normalizacion de resultado tipo `SANGRE`;
- validacion de revision con etiquetas de saliva;
- rechazo de `nucleo` en revision tipo `SANGRE`;
- resumen de revision usando etiquetas de sangre.

## Validaciones ejecutadas

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py check
```

Resultado:

```text
PASS - System check identified no issues (0 silenced).
```

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py makemigrations --check
```

Resultado:

```text
PASS - No changes detected.
```

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' -m pytest
```

Resultado:

```text
PASS - 116 passed, 2 skipped.
```

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
PASS - 98 tests OK.
```

```powershell
npm.cmd run build
```

Resultado:

```text
PASS fuera del sandbox - vite build completo.
```

Nota: el primer intento dentro del sandbox fallo por el bloqueo conocido de Vite/esbuild al leer `vite.config.js` desde esta ruta. La validacion fuera del sandbox paso correctamente.

## Sprint siguiente recomendado

Sprint 16A resolvio el cambio relacional minimo con `MuestraSangre` y una estrategia transicional compatible con `MuestraSaliva`. Sprint 16B agrego el endpoint backend de segmentacion de sangre.

Los siguientes sprints deberian decidir si:

- se mantiene la estrategia transicional de dos FK mientras se integra sangre;
- se agrega UI para sangre sobre `MuestraSangre`;
- se evalua mas adelante un modelo comun `ImagenMuestra` con una migracion mas amplia.
