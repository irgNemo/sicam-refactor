# ADR-003 - Generalize Sample Images

## Status

Proposed

## Context

The backend currently models only `MuestraSaliva`. SICAM must process saliva and blood samples.

## Decision

Introduce a general sample image model with a sample type field.

Preferred name:

```text
ImagenMuestra
```

Fields:

```text
analysis_id
tipo_muestra: SALIVA | SANGRE
imagen
estado_procesamiento
fecha_subida
```

## Consequences

Positive:

- One upload workflow.
- Correct routing to saliva or blood segmentation.
- Cleaner reporting and characterization.

Negative:

- Requires migration from `MuestraSaliva`.
- Requires frontend changes.
