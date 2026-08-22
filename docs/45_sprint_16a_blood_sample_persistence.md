# Sprint 16A - Persistencia de MuestraSangre y soporte relacional

## Proposito

Resolver el bloqueo de persistencia relacional para muestras de sangre sin activar todavia el flujo end-to-end contra `apps/segmentation-blood`.

Este sprint agrega capacidad de representar una muestra de sangre en Django y asociar un `ResultadoSegmentacion` a saliva o sangre, manteniendo un unico modelo de resultado, un unico modelo de revision y el resolvedor efectivo existente.

## Blocker inicial

Antes de este sprint:

- Django solo tenia `MuestraSaliva`.
- `ResultadoSegmentacion.muestra` apuntaba obligatoriamente a `MuestraSaliva`.
- No existia una relacion persistente para resultados de segmentacion de sangre.

## Valores historicos revisados

Antes de crear la migracion se inspecciono la base local:

```text
ResultadoSegmentacion por tipo_muestra:
SALIVA: 11

ResultadoSegmentacion con muestra NULL:
0
```

Todos los historicos existentes tenian `tipo_muestra='SALIVA'` y `muestra` no nula. Por eso no se agrego `RunPython`: no habia datos ambiguos ni normalizacion necesaria antes del constraint.

## Opciones evaluadas

### Opcion elegida: dos FK transicionales

```text
ResultadoSegmentacion
  muestra -> MuestraSaliva nullable
  muestra_sangre -> MuestraSangre nullable
  tipo_muestra -> SALIVA / SANGRE
```

Motivos:

- mantiene compatibilidad con `resultado.muestra` para saliva;
- conserva integridad referencial SQL;
- evita duplicar `ResultadoSegmentacion`;
- permite avanzar a sangre sin una migracion grande de dominio;
- hace explicita la transicion.

### Opcion descartada: GenericForeignKey

No se uso `GenericForeignKey` porque debilita la integridad referencial, complica constraints SQL y hace menos auditable la relacion real entre resultado y muestra.

### Opcion descartada: ImagenMuestra en este sprint

`ImagenMuestra` sigue siendo una opcion de dominio mas limpia, pero exige migrar o compatibilizar `MuestraSaliva`, ajustar endpoints y preparar frontend. Eso seria un cambio mas amplio que Sprint 16A.

### Opcion descartada: modelos paralelos

No se creo `ResultadoSegmentacionSangre` ni `RevisionSegmentacionSangre` porque duplicarian el dominio y romperian el principio de un resultado y una revision comunes para ambos tipos.

## MuestraSangre

Modelo agregado:

```text
MuestraSangre
  id_muestra: AutoField primary key
  analisis: ForeignKey(AnalisisPred, related_name="muestras_sangre")
  imagen: ImageField(upload_to="muestras/sangre/%Y/%m/")
  fecha_subida: DateTimeField(auto_now_add=True)
```

La relacion padre sigue el mismo patron que `MuestraSaliva`:

```text
AnalisisPred -> MuestraSangre
```

No se agregaron campos clinicos ni cientificos especulativos.

## ResultadoSegmentacion

`ResultadoSegmentacion` se mantiene como unico modelo para ambos tipos.

Campos preservados:

- `respuesta_json`
- `resultado_normalizado`
- `estado`
- `error`
- `creado_en`
- `actualizado_en`
- `tipo_muestra`

Cambios:

- `muestra` ahora permite `null=True, blank=True` para soportar resultados de sangre.
- Se agrego `muestra_sangre` como `ForeignKey(MuestraSangre, null=True, blank=True)`.

## Constraint de consistencia

Se agrego el constraint:

```text
resultado_segmentacion_sample_type_consistency
```

Reglas permitidas:

```text
tipo_muestra = SALIVA
AND muestra IS NOT NULL
AND muestra_sangre IS NULL
```

o:

```text
tipo_muestra = SANGRE
AND muestra IS NULL
AND muestra_sangre IS NOT NULL
```

Estados rechazados:

- `SALIVA` sin `muestra`;
- `SANGRE` sin `muestra_sangre`;
- `SALIVA` con `muestra_sangre`;
- `SANGRE` con `muestra`;
- ambas relaciones definidas simultaneamente.

## Compatibilidad de saliva

El nombre `muestra` se preserva. El codigo y frontend actuales que usan resultados de saliva pueden seguir resolviendo:

```python
resultado.muestra
```

Los endpoints publicos actuales de saliva no se cambiaron.

## RevisionSegmentacion

No se cambio la estructura de `RevisionSegmentacion`.

La relacion sigue siendo:

```text
RevisionSegmentacion -> ResultadoSegmentacion
```

La validacion por etiquetas ya estaba preparada desde Sprint 15 con `resultado_segmentacion.tipo_muestra`.

## Resultado efectivo

No se creo un resolvedor separado para sangre.

El resolvedor actual sigue operando sobre:

```text
ResultadoSegmentacion
RevisionSegmentacion
```

Se agregaron pruebas para confirmar:

- `ResultadoSegmentacion` de sangre automatico -> fuente `AUTOMATICO`;
- `RevisionSegmentacion` de sangre `VALIDADA` -> fuente `VALIDADA`.

## Migracion

Migracion creada:

```text
api/migrations/0005_alter_resultadosegmentacion_muestra_muestrasangre_and_more.py
```

Operaciones:

1. `AlterField` sobre `ResultadoSegmentacion.muestra` para permitir `null=True, blank=True`.
2. `CreateModel` de `MuestraSangre`.
3. `AddField` de `ResultadoSegmentacion.muestra_sangre`.
4. `AddConstraint` `resultado_segmentacion_sample_type_consistency`.

No incluye `RunPython` porque los historicos inspeccionados ya cumplian la restriccion futura.

## Riesgo de rollback

La migracion inversa puede eliminar la tabla `MuestraSangre` y el campo `muestra_sangre`. Mientras no existan datos reales de sangre, el rollback es razonable. Una vez que se creen resultados reales de sangre, revertir esta migracion implicaria perdida de esa persistencia salvo que antes se migren/exporten esos datos.

## Tests agregados

### Saliva

- `ResultadoSegmentacion` de saliva sigue creandose con `muestra`.
- `resultado.muestra` sigue devolviendo `MuestraSaliva`.

### Sangre

- Se puede crear `MuestraSangre`.
- Se puede crear `ResultadoSegmentacion` con `tipo_muestra='SANGRE'` y `muestra_sangre`.
- Una revision de sangre permite `membrana`.
- Una revision de sangre permite `micronucleo`.
- Una revision de sangre rechaza `nucleo`.
- El resultado efectivo automatico de sangre funciona.
- El resultado efectivo con revision validada de sangre funciona.

### Integridad

Se cubrieron estados invalidos por constraint:

- `SALIVA` sin muestra;
- `SANGRE` sin muestra;
- `SALIVA` con muestra de sangre;
- `SANGRE` con muestra de saliva;
- ambas FK definidas.

## Validaciones

Ver resumen final del sprint para resultados exactos.

Comandos:

```powershell
python manage.py check
python manage.py makemigrations --check
python -m pytest
python manage.py test
git diff --check
```

## Pendiente para Sprint 16B

Sprint 16B deberia encargarse de conectar el flujo Django hacia `apps/segmentation-blood`:

- endpoint Django para segmentar una `MuestraSangre`;
- lectura de bytes de `MuestraSangre.imagen`;
- llamada a `segment_image("SANGRE", ...)`;
- normalizacion `sample_type="SANGRE"`;
- persistencia de `ResultadoSegmentacion(muestra_sangre=...)`;
- pruebas con mocks, sin levantar el microservicio real.
