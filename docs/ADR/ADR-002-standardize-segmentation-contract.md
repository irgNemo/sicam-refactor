# ADR-002 - Standardize Segmentation Contract

## Status

Proposed

## Context

Both segmentation microservices return similar polygon objects:

```json
{
  "objetos": [
    {
      "id": 1,
      "tipo": "membrana",
      "puntos": [[10, 20]]
    }
  ]
}
```

The structure is useful but implicit.

## Decision

Preserve the existing contract for compatibility, but document it and introduce formal schemas.

## Current Contract

```text
objetos: list
objetos[].id: integer
objetos[].tipo: membrana | nucleo | micronucleo
objetos[].puntos: list of [x, y]
```

## Future Contract

Introduce normalized English/internal names only after current code is stable.

## Consequences

Positive:

- Reduced risk of breaking frontend/backend integration.
- Easier tests.
- Easier Codex refactors.

Negative:

- Short-term bilingual naming remains.
