# ADR-001 - Keep Django as the Segmentation Orchestrator

## Status

Proposed

## Context

The system has a Vue frontend, a Django backend and two FastAPI segmentation microservices. The frontend currently talks only to Django. The segmentation services are not yet integrated.

## Decision

Django should be the orchestrator for segmentation workflows.

The frontend should not call FastAPI microservices directly.

## Rationale

Django owns:

- Authentication
- Patient/case/sample identity
- Persistence
- Clinical traceability
- Future authorization rules

Therefore, it should decide which segmentation service to call and persist the result.

## Consequences

Positive:

- Centralized security and auditing.
- Easier frontend.
- Microservice URLs hidden from browser.
- Easier persistence and retry logic.

Negative:

- Django must handle network failures.
- Django must define timeout/error policies.
- Longer request duration unless background tasks are introduced.
