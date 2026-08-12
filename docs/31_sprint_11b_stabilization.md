# Sprint 11B - Stabilization of Overlay Controls and Normalized Result Contract

## Fecha

2026-08-11 15:35:50 -06:00

## Referencia Git

- Rama: `master`
- Commit base observado: `da3f4ea`

## Alcance

Estabilizacion puntual posterior a la validacion manual end-to-end del flujo:

```text
Frontend Vue -> Django REST -> FastAPI saliva -> ResultadoSegmentacion -> resultado_normalizado -> historial -> overlay SVG
```

No se modificaron microservicios, algoritmos de segmentacion, `cellpose/`, modelos Django, endpoints ni migraciones.

## Defectos Diagnosticados

### A. Visibilidad por etiqueta

La primera correccion agrego keys defensivas y un setter explicito para los controles del bloque `Etiquetas del overlay`, pero la validacion manual posterior mostro que el usuario interactuaba naturalmente con otro grupo visual: la tarjeta legacy `Objetos Detectados`.

No existia un fallo de reactividad del overlay. Habia dos grupos de checkboxes; la tarjeta legacy `Objetos Detectados` no estaba conectada al estado de visibilidad.

Causa raiz confirmada:

- `resultado_normalizado.objects[].id` no era confiable como identificador unico en resultados existentes.
- La UI usaba keys que podian depender de `object.id`.
- Existia un grupo funcional `Etiquetas del overlay`.
- Existia un segundo grupo legacy `Objetos Detectados`.
- Los checkboxes de `Objetos Detectados` eran HTML estaticos con `checked`, sin `@change`, sin `v-model` y sin conexion con `overlayLabelVisibility`.

Correccion:

- Se agregaron keys defensivas con indice estable.
- Se reemplazo el manejo del checkbox por `setOverlayLabelVisibility(label, checked)`.
- Se elimino la UI redundante `Etiquetas del overlay`.
- La tarjeta `Objetos Detectados` se convirtio en el unico control canonico de visibilidad.
- Sus filas ahora se derivan de `overlayLabels`, muestran conteos reales y actualizan `overlayLabelVisibility`.
- `overlayVisibleDrawableObjects` sigue filtrando por `overlayLabelVisibility[label] !== false`.

### B. Zoom, Rotar y Ajustar

Los botones estaban presentes en la interfaz, pero no tenian estado ni handlers asociados.

Causa raiz confirmada:

- No existian `imageZoom` ni `imageRotation`.
- No habia metodos para aplicar zoom, rotacion o restaurar vista.
- No habia transformacion CSS compartida para imagen y SVG.

Correccion:

- Se agrego estado minimo:

```text
imageZoom = 1
imageRotation = 0
```

- `Zoom` incrementa en pasos de `0.25` hasta un maximo de `2.0`.
- `Rotar` incrementa `90` grados por click, modulo `360`.
- `Ajustar` restaura `imageZoom = 1` e `imageRotation = 0`.
- La transformacion se aplica a un wrapper comun de imagen y SVG:

```text
transform: scale(...) rotate(...)
transform-origin: center center
```

Esto mantiene la alineacion porque imagen y overlay comparten el mismo sistema transformado.

### C. IDs normalizados duplicados

El normalizador usaba el `id` crudo del microservicio como `object.id`. En segmentacion real se observaron multiples objetos con `id = 255`, especialmente nucleos y micronucleos.

Causa raiz confirmada:

- `object.id` normalizado heredaba `raw_object.id`.
- El `id` crudo no es unico globalmente dentro del resultado.

Correccion:

- Se implemento contrato normalizado `version = "1.1"`.
- `object.id` ahora es secuencial y unico dentro del resultado: `1..N`.
- `source.raw_id` conserva el `raw_object.id` original.
- `source.raw_type` conserva el tipo original.
- `respuesta_json` permanece intacta.
- `raw_result` no se modifica.
- `summary.total_objects` y `summary.counts_by_label` conservan la misma semantica.

Ejemplo:

```json
{
  "version": "1.1",
  "objects": [
    {
      "id": 31,
      "label": "nucleo",
      "geometry": {},
      "source": {
        "raw_id": 255,
        "raw_type": "nucleo"
      }
    }
  ]
}
```

### D. Warnings `patientId` y `caseId`

Vue reportaba:

```text
Invalid prop: type check failed for prop "patientId". Expected String, got Number.
Invalid prop: type check failed for prop "caseId". Expected String, got Number.
```

Causa raiz confirmada:

- Django entrega IDs numericos.
- `SideBar.vue` emite IDs numericos.
- `MainContent.vue` declaraba `patientId` y `caseId` como `String`.

Correccion:

- `patientId` y `caseId` ahora usan `Number` como tipo canonico en `MainContent.vue`.

## Contrato Normalizado 1.1

La version `1.1` cambia la semantica de `objects[].id`:

- `objects[].id`: identificador interno normalizado, unico y secuencial.
- `objects[].source.raw_id`: identificador original del microservicio.
- `objects[].source.raw_type`: tipo original del microservicio.

Compatibilidad con `1.0`:

- No se modifican historicos.
- El frontend no asume unicidad de `object.id`.
- Las keys de renderizado incluyen indice estable para evitar colisiones.

## Pruebas Backend Agregadas o Ajustadas

Se agregaron verificaciones para:

- IDs normalizados unicos.
- IDs secuenciales `1..N`.
- `raw_id` preservado.
- `raw_type` preservado.
- multiples objetos raw con `id = 255` producen IDs normalizados distintos.
- `summary.total_objects` no cambia.
- `summary.counts_by_label` no cambia.
- `raw_result` no se modifica.
- el endpoint devuelve `version = "1.1"`.
- el endpoint persiste `version = "1.1"`.

## Validaciones Ejecutadas

### Backend

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
PASS - 53 passed, 2 skipped.
```

```powershell
& 'C:\Users\israe\miniconda3\envs\sicam\python.exe' manage.py test
```

Resultado:

```text
PASS - Ran 35 tests. OK.
```

### Frontend

```powershell
npm.cmd run build
```

Resultado:

```text
PASS - vite build completado.
```

Nota: dentro del sandbox inicial fallo por permisos de Windows al resolver `vite.config.js`; ejecutado fuera del sandbox, el build paso. PowerShell emitio una advertencia local sobre `profile.ps1`, no relacionada con el proyecto.

## Checklist Manual Pendiente

Como no existe framework de pruebas frontend automatizadas, queda pendiente validar en navegador:

- Ocultar `membrana`.
- Mostrar `membrana`.
- Ocultar `nucleo`.
- Mostrar `nucleo`.
- Ocultar `micronucleo`.
- Mostrar `micronucleo`.
- Confirmar que solo cambia la etiqueta elegida.
- Confirmar que `Zoom` mantiene la alineacion imagen-overlay.
- Confirmar que `Rotar` mantiene la alineacion imagen-overlay.
- Confirmar que `Ajustar` restaura zoom y rotacion.
- Confirmar que resize mantiene la alineacion.
- Confirmar que cambiar de muestra restaura zoom y rotacion.
- Confirmar que no aparecen warnings de `patientId` ni `caseId`.

## Limitaciones

- No se realizo backfill de resultados historicos `version = "1.0"`.
- No se agrego edicion manual de poligonos.
- No se agrego `canvas`.
- No se agregaron dependencias.
- No se automatizaron pruebas visuales del overlay.

## Conclusion

PASS WITH MANUAL UI CHECKLIST

El backend queda validado automaticamente. El frontend compila correctamente y queda pendiente la verificacion manual del comportamiento visual interactivo en navegador.
