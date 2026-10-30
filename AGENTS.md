# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Stack

Monorepo: Django REST (`apps/web/Backend`) + Vue 3/Vite (`apps/web/Frontend`) + three FastAPI microservices. Three **separate** Conda environments; never mix them.

| Component | Directory | Conda env | Port |
|---|---|---|---|
| Django | `apps/web/Backend` | `sicam` (Python 3.10.20) | 8000 |
| SALIVA CURRENT | `apps/segmentation-saliva` | `sicam` | 8001 |
| BLOOD | `apps/segmentation-blood` | `sicam-blood` (Python 3.10.21) | 8002 |
| SALIVA ALT | `apps/segmentation-saliva-alt` | `sicam-saliva-alt` (Python 3.10.20) | 8003 |
| Frontend | `apps/web/Frontend` | nvm (Node 24.17.0) | 5173 |

## Commands

All commands must be run from the component's own directory with its Conda env active.

### Django (from `apps/web/Backend`, env `sicam`)
```bash
python manage.py runserver 127.0.0.1:8000
python manage.py migrate && python manage.py check
python manage.py seed_demo_data          # creates demo patient/case with 1×1 PNG (not for inference)
python -m pytest -q                      # all tests (simulates HTTP; no Cellpose needed)
python -m pytest api/test_saliva_strategies.py -q   # single file
python manage.py test                    # Django test runner (alternative)
```

### Frontend (from `apps/web/Frontend`, nvm)
```bash
npm run dev -- --host 127.0.0.1 --port 5173
node --test tests/*.test.mjs             # all tests (no `npm test` script exists)
node --test tests/auth.test.mjs          # single test file
npm run build
npm run lint                             # runs eslint --fix --cache (modifies files)
node_modules/.bin/eslint .               # lint without auto-fix
```

### Microservices (each from its own directory, own Conda env)
```bash
# SALIVA CURRENT and ALT
python -m uvicorn app.main:app --host 127.0.0.1 --port <8001|8003>

# BLOOD — entrypoint is main.py at root, NOT app/main.py
python -m uvicorn main:app --host 127.0.0.1 --port 8002

# ALT optional tests (from apps/segmentation-saliva-alt)
python -m pip install -r requirements-test.txt
python -m pytest -q
```

## Critical Non-Obvious Rules

### Python environments
- **Never install Cellpose PyPI in `sicam` or `sicam-blood`** — they use vendored Cellpose at `segmentacion_core/cellpose/`.
- BLOOD's `requirements.txt` contains `-e .` and **must be installed from `apps/segmentation-blood`** (not from repo root).
- ALT's `requirements.txt` starts with `-c constraints.txt`; always use the file, not a direct `pip install cellpose`.
- Django settings only load `.env` when `DJANGO_ENV=development` (default). Production reads only process environment.

### Models (not versioned, must be provisioned manually)
- SALIVA CURRENT loads `apps/segmentation-saliva/segmentacion_core/membranas_500_125` at import time. Importing `app.main` triggers model load — don't do it for lightweight checks.
- BLOOD and ALT share `~/.cellpose/models/cpsam` (SHA-256 `e1440...abe2`, 1233587898 bytes). ALT verifies hash/size at startup and **fails hard** if wrong — no fallback.

### Backend test fixtures
- All pre-18T tests use `PlatformAPITestCase` from `api/testing.py` (not Django's `APITestCase` directly). It auto-injects `institution` into POST `/api/pacientes/` and `/api/acquisition-profiles/`.
- Security/role tests use DRF's unmodified `APIClient` instead.
- `pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings`; tests run from `apps/web/Backend`.

### Frontend tests
- Tests use Node's built-in test runner (`node:test`), **not vitest or Jest**. Run with `node --test tests/<file>.test.mjs`.
- Tests spin up a Vite dev server in SSR/middleware mode to load Vue components. No separate test framework dependencies.
- `--test-isolation=none` is used when running all 11 files: `node --test --test-isolation=none tests/<archivo>.test.mjs`.

### Authentication / CSRF
- Axios is configured with `withCredentials: true`, `withXSRFToken: true`, `xsrfCookieName: "csrftoken"`. No proxy Vite.
- **Always access via `http://127.0.0.1:5173`**, not `http://localhost:5173`. Vite redirects localhost → 127.0.0.1 (307) via `dev/canonicalOrigin.mjs` to avoid SameSite=Lax cookie issues. `localhost` and `127.0.0.1` are different sites.
- `/api/auth/me/` returns `200` with `user: null` when unauthenticated (not 401). `AuthGate` checks this to decide whether to show login.

### Segmentation strategy routing
- Django uses `SEGMENTATION_SERVICES['SALIVA']` for CURRENT and `SALIVA_ALT_SEGMENTATION_SERVICE` for ALT — two different settings keys.
- BLOOD endpoint is `/api/v1/segmentar`; SALIVA endpoints are `/segmentar`.
- BLOOD rejects `segmentation_strategy` field entirely, even `null`. SALIVA defaults to `CURRENT_CUSTOM_V1` if omitted.
- Segmentation effective-result semantics are defined in "Scientific and Data Integrity Rules" below. In particular, BORRADOR is never effective and a MANUAL/AUTOMATIC base may remain effective when there is no VALIDADA snapshot. 

### UI context persistence
- Tab/patient/case/sample state is stored in `sessionStorage` under key `sicam.uiContext.v1`. Auth context under `sicam.auth.context`. Restarting Vite/Django does **not** clear this.

## Code Style

### Frontend (Vue 3 Options API)
- Vue uses **Options API** throughout (not Composition API).
- 2-space indent, LF line endings, UTF-8, max line length 100 (`apps/web/Frontend/.editorconfig`).
- `@` alias resolves to `src/`. Domain logic in `src/domain/`, API calls in `src/services/`, UI components in `src/components/`.
- Frozen `Object.freeze()` constants for strategy/type enums in `src/domain/`.

### Backend (Django)
- Domain models inherit from `ArchivableModel`, `AuthoredModel` from `api/access_models.py` and `api/lifecycle_models.py`.
- All strategy constants use `django.db.models.TextChoices` (see `api/segmentation_strategies.py`).
- Never edit `settings.py` to change a local URL — use `.env`.

## Scientific and Data Integrity Rules

These rules are project invariants. Do not reinterpret them from implementation
details.

### Effective segmentation

`AUTOMATICO != VALIDADO`.

The effective segmentation contract is:

```text
if a VALIDADA revision exists as the effective validated snapshot:
    effective segmentation = validated snapshot
else:
    effective segmentation = base MANUAL or AUTOMATIC result
```

A `BORRADOR` revision is never effective.

The existence of a BORRADOR must not hide or replace an otherwise valid base
MANUAL/AUTOMATIC segmentation.

Do not infer a segmentation strategy from filenames, model artifacts, patient
metadata or historical conventions.

### Characterization versions

Characterization scientific versions are immutable historical contracts.

Current established versions:

- 2.1: historical pixel-based Characterization.
- 2.2: provenance/calibration-aware Characterization preserving the accepted
  2.1 pixel semantics.
- 2.3: feature-gap version extending 2.2. Implemented in Sprint 18U-C1.
  Adds `elongation_index`, `convex_solidity`, `mn_nucleus_perimeter_ratio_px`,
  `mn_nucleus_perimeter_ratio_physical`, `mn_nucleus_min_distance_px`,
  `mn_nucleus_min_distance_um`.

Never:

- relabel an existing Characterization as another version;
- silently change the scientific meaning of an existing version;
- rewrite historical Characterization rows to match newer algorithms.

A new scientific definition requires a new Characterization version.

### Current Characterization 2.3 work

The intended 2.3 feature-gap closure concerns the historical Excel variables:

- Elipticidad
- Solidez
- Relacion_Proporcion_perimetro_MN_sobre_nucleo
- Relacion_Distancia_borde_MN_nucleo_px

These must not be invented from naming conventions.

In particular:

- `Elipticidad` is not the same metric as `Excentricidad`.
- edge-to-edge MN–nucleus distance is not centroid-to-centroid distance.
- relationship metrics use the **characterization-time** MN ↔ nucleus association.
- absence of an MN produces null relationship values, not zero.

Historical provenance must be established before claiming numerical parity.

**MN ↔ nucleus association — corrected architecture note (Sprint 18U-C1):**

The association is **reconstructed deterministically during Characterization**,
NOT stored in the segmentation payload:

1. `_associate_to_membranes()` assigns each MN to exactly one membrane via
   centroid-in-polygon test.
2. `_nearest_nucleus()` selects, within the MN's membrane, the nucleus with
   minimum Euclidean centroid distance in **pixel space**. Tie-break: lower ID.
3. The resulting `nucleus_id` is **written into the Characterization JSON**.

All 2.3 relational metrics (perimeter ratio, minimum separation) use this
`nucleus_id` already computed during the same Characterization pass.
They must NOT independently select a nucleus.

Reproducibility: deterministic from the polygon data in the effective
segmentation. If the effective segmentation changes (new VALIDADA revision),
the fingerprint changes and a new Characterization is created.

### Dataset Builder

Generated datasets are immutable scientific snapshots.

Never rewrite an existing GENERATED dataset, manifest, frozen source reference,
class assignment or content hash.

Current SALIVA nuclear-feature row grain:

`NUCLEUS_MN_RELATION`

Semantics:

- nucleus with no associated MN → one row;
- nucleus with one MN → one row;
- nucleus with multiple MN → one row per persisted MN association.

Do not produce Cartesian products.

For supervised datasets:

- classes are dataset-local;
- diagnoses/classes must never be inferred from patient identity or metadata;
- at least two effective classes are required for generation;
- a zero-row patient is auditable and may remain selected;
- a zero-row class does not count as an effective class.

Any future train/validation/test split must be grouped by PATIENT, never by
image, nucleus or MN.

### Privacy

Do not export or expose patient PII in datasets, manifests, audit reports or
test artifacts.

Avoid:

- names;
- birth dates;
- email;
- phone;
- hospital/external authority identifiers.

Use the project's local/pseudonymous identifiers where applicable.

Never infer diagnosis from identifiers or initials.

### Calibration

Current relevant calibration:

`CAL-OPTIKA-40X-PROVISIONAL-001`

with:

```text
sx = 0.055233934048 um/px
sy = 0.055010060892 um/px
```

Its state remains:

`PROVISIONAL`

Do not promote it to final/accepted calibration.

Physical measurements may be technically computable but must not be described
as scientifically final while calibration remains provisional.

Important open scientific item:

`IMPORTANT_PENDING_18S_A2`

It requires final evaluation of independent captures, repositioning, rotation,
repeatability, anisotropy, uncertainty and acceptance tolerances.

### Physical geometry

Calibration may be anisotropic (`sx != sy`).

For physical geometric distances or perimeters, transform coordinates into
physical space first when required by the scientific algorithm:

```text
x_um = x_px * sx
y_um = y_px * sy
```

Do not generally replace anisotropic geometry with a single average scale.

### GLCM

Current GLCM methodology remains the accepted Characterization contract unless
a new version explicitly changes it.

Open item:

`GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING`

Do not claim that the current `d = 1 px` GLCM is normalized to a fixed physical
distance.

### Deferred Characterization backfill

The previously proposed Characterization 2.2 backfill remains deferred:

`PENDING_CHARACTERIZATION_22_BACKFILL`

Do not execute a real-data backfill unless a later sprint explicitly authorizes
it.

After Characterization 2.3 is accepted, reassess whether any future backfill
should target 2.2 or 2.3.

### Known scientific remediation items

Do not automatically remediate these:

- samples historically associated with pending membrane review, including
  current mappings related to samples 56, 58, 62 and 63;
- ImageJ `PAIR_008 / REAL_HOLE` historical issue;
- missing or incomplete Characterization;
- AcquisitionSeries/calibration associations.

Always resolve current database state before acting; historical numeric IDs or
aliases must not be assumed to remain equivalent.

### BLOOD

BLOOD segmentation does not use the SALIVA nucleus/MN scientific contract.

Do not reuse SALIVA nucleus-specific assumptions for BLOOD.

## Real Data Safety

Unless a sprint explicitly authorizes a real-data operation:

DO NOT:

- run segmentation on real samples;
- run Characterization on real samples;
- backfill Characterization;
- validate or modify segmentation revisions;
- assign or reassign AcquisitionSeries;
- modify calibration records;
- create or regenerate real scientific datasets;
- archive/unarchive scientific records;
- delete scientific rows;
- modify media files.

Prefer automated tests with the test database.

If a sprint requires real-data inspection, perform it read-only unless explicit
write authorization is present.

## Database and Media Integrity

For scientific or migration-related work, preserve existing integrity checks.

When requested by the sprint, verify:

```text
SQLite integrity_check = ok
foreign_key_check = no violations
```

Relevant scientific records include at least:

- patients;
- cases;
- analyses;
- samples;
- segmentation results;
- revisions;
- Characterizations;
- AcquisitionSeries;
- calibrations;
- datasets;
- dataset patients;
- dataset samples;
- LifecycleEvents.

Do not modify real media unless explicitly authorized.

## Git Safety for AI Agents

Multiple AI agents may work on this repository, but only one implementation
agent should edit the working tree at a time.

Before editing:

```bash
git branch --show-current
git status --short
git log -5 --oneline
git diff --check
```

Preserve unrelated changes.

Never use destructive cleanup merely to obtain a clean tree:

```text
git reset --hard
git checkout .
git clean -fd
```

unless the user explicitly authorizes that exact operation.

Do not commit or push unless explicitly requested.

When switching between Bob, Codex or another implementation agent, inspect the
current working tree first and treat existing changes as intentional until
proven otherwise.

## Agent Working Method

For scientific changes:

1. inspect current implementation and documentation;
2. establish the scientific definition/provenance;
3. report unresolved ambiguity rather than inventing a convention;
4. implement the smallest versioned change;
5. run targeted tests;
6. run full affected regression once when stable;
7. verify real scientific data were not unintentionally modified;
8. report pending scientific decisions separately from software PASS/FAIL.

Repository code and accepted project documentation are the source of truth for
current implementation.

Scientific project invariants in this file take precedence over assumptions
derived from naming, common conventions or legacy code.
