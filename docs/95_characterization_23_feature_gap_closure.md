# Sprint 18U-C1 — Characterization 2.3 Feature-Gap Closure

## Overview

This sprint implements Characterization version 2.3, closing the four-metric
feature gap identified in Sprint 18U-B (Dataset Builder) and confirmed by the
18U-C0 data readiness audit.

Characterization 2.3 is strictly additive. Every 2.1 and 2.2 result remains
scientifically unchanged.

---

## New Metrics

### Elongation Index (`elongation_index`)

**Scientific formula:** `E = 1 − sqrt(λ_min / λ_max) = 1 − b/a`

**SICAM 2.3 implementation:**

```
E = 1 − sqrt(clamp(1 − eccentricity², 0, 1))
```

Derived from the existing stored `eccentricity` value. No re-rasterization.

**Derivation:** Since `eccentricity = sqrt(1 − λ_min/λ_max)`, it follows that
`λ_min/λ_max = 1 − eccentricity²`, and therefore
`E = 1 − sqrt(λ_min/λ_max) = 1 − sqrt(1 − eccentricity²)`.

This is algebraically identical to the eigenvalue formula and guaranteed to use
the same raster-moment geometry as SICAM eccentricity.

| Case | Value |
|---|---|
| `eccentricity = None` | `elongation_index = None` |
| `eccentricity = 0` (circle) | `elongation_index = 0` |
| `eccentricity = 1` (line) | `elongation_index = 1` |
| Intermediate | strictly between 0 and 1 |

Entity scope: nucleus and micronucleus.
Physical counterpart: none in this sprint.

---

### Convex Solidity (`convex_solidity`)

**Formula:** `S = area_px2 / polygon_area(convex_hull(points))`

The numerator is the existing `area_px2` from the 2.2 result metrics (not
recomputed). The denominator is the area of the convex hull of the object's
polygon, computed via Andrew's Monotonic Chain.

| Case | Value |
|---|---|
| `area_px2` missing or ≤ 0 | `convex_solidity = None` |
| hull degenerate (collinear) | `convex_solidity = None` |
| hull area ≤ ε | `convex_solidity = None` |
| convex polygon | `convex_solidity = 1.0` |
| concave polygon | `0 < convex_solidity < 1` |

Entity scope: nucleus and micronucleus.
Physical counterpart: none (ratio is invariant under uniform scale; anisotropic
affine transforms change numerator and denominator equally).

---

### MN–Nucleus Perimeter Ratio — Pixel (`mn_nucleus_perimeter_ratio_px`)

**Formula:** `R_P_px = perimeter_mn_px / perimeter_nucleus_px`

Read directly from existing `perimeter_px` in the 2.2 result metrics.

| Case | Value |
|---|---|
| no associated nucleus | `None` |
| `perimeter_nucleus_px = 0` or `None` | `None` |
| `perimeter_mn_px = None` | `None` |

Entity scope: relation (MN level). Multiple MN per nucleus → one ratio per MN.

---

### MN–Nucleus Perimeter Ratio — Physical (`mn_nucleus_perimeter_ratio_physical`)

**Formula:** `R_P_phys = perimeter_mn_um / perimeter_nucleus_um`

Read directly from existing `perimeter_um` in the 2.2 result metrics.

Under anisotropic calibration (`sx ≠ sy`), polygon perimeter transforms
non-linearly. Therefore `R_P_px ≠ R_P_physical` in general.

| Case | Value |
|---|---|
| no physical calibration | `None` |
| same null conditions as pixel version applied to `_um` fields | `None` |

---

### Minimum MN–Nucleus Separation — Pixel (`mn_nucleus_min_distance_px`)

**Definition:** Minimum Euclidean distance between the two **closed polygonal
sets** (filled regions). Returns 0 for touching, intersecting, overlapping, or
containment.

Algorithm uses existing `minimum_polygon_distance()` in `geometry.py`.

| Case | Value |
|---|---|
| no associated nucleus | `None` |
| either polygon invalid/degenerate | `None` |
| touching or overlapping | `0` |
| separated | `> 0` |

Entity scope: relation (MN level).
Units: px.

---

### Minimum MN–Nucleus Separation — Physical (`mn_nucleus_min_distance_um`)

Same algorithm as pixel version, applied after per-coordinate transform:

```
x_um = x_px * sx
y_um = y_px * sy
```

**Must NOT use** `distance_px × average_scale` — this is scientifically invalid
under anisotropic calibration.

Units: µm.

Physical status: PROVISIONAL while `CAL-OPTIKA-40X-PROVISIONAL-001` is
PROVISIONAL. `IMPORTANT_PENDING_18S_A2` preserved.

---

## Architecture

### Version isolation

| Layer | Function | Produces 2.3 keys? |
|---|---|---|
| Pixel (2.1) | `characterize_saliva_result()` in `saliva.py` | NO |
| Physical (2.2 intermediate) | `extend_physical_result()` in `physical.py` | NO |
| 2.3 extension | `extend_23_metrics()` in `physical.py` | YES — sole producer |

`saliva.py` and `raster_metrics.py` are **not modified** in this sprint.

### `extend_23_metrics()` chain in `service.py`

```python
pixel_result    = characterize_effective_segmentation(...)          # v2.1
physical_result = extend_physical_result(..., version='2.2')        # v2.2 intermediate
if algorithm_version == '2.3':
    resultado_json  = extend_23_metrics(physical_result, ...)       # v2.3 final
else:
    resultado_json  = physical_result                               # v2.2 (or other)
```

### Version fields in 2.3 JSON

```json
{
  "version": "2.3",
  "schema_version": "2.3",
  "characterization_version": "2.3",
  "provenance": {
    "pixel_algorithm_version": "2.1",
    "GLCM_PHYSICAL_DISTANCE_NORMALIZATION": "PENDING_SCIENTIFIC_DECISION",
    "IMPORTANT_PENDING_18S_A2": true
  }
}
```

### Fingerprint

Fingerprint includes the version string `'2.3'`. 2.3 fingerprints are always
distinct from 2.2 fingerprints for the same segmentation data. Existing 2.1 and
2.2 records are untouched.

---

## New Geometry Helpers (`geometry.py`)

| Function | Description |
|---|---|
| `polygon_convex_hull(points)` | Andrew's Monotonic Chain; returns `None` for degenerate/collinear |
| `polygon_convex_hull_area(points)` | Calls hull then `polygon_area` |
| `minimum_polygon_distance(a, b)` | Closed-set minimum Euclidean distance; 0 for overlap/touch/containment |
| `_point_to_segment_distance(p, a, b)` | Point-to-segment with clamped projection |
| `_segment_to_segment_distance(p1, p2, p3, p4)` | Min of four point-to-segment distances |

---

## Dataset Builder Changes

### `features.py`

- All existing features gain `min_version='2.1'` field.
- Six new 2.3 features added with `min_version='2.3'`.
- `UNAVAILABLE` is now empty (all four legacy gaps closed).
- `SCHEMA_VERSION` bumped to `'saliva-nuclear-2'`.

### `dataset_views.py`

- `'2.3'` added to `ChoiceField` and options endpoint response.
- `_parse_version()` utility added (tuple comparison, safe for `'2.10'`, etc.).
- Serializer `validate()` rejects 2.3-only features when version is `'2.1'` or
  `'2.2'` with a 400 error.
- Options endpoint returns `schema_version` field.

### New 2.3 Dataset Builder features

| key | entity | label | group | pixel path | physical path |
|---|---|---|---|---|---|
| `nucleus_elongation` | nucleus | `Indice_elongacion` | Morfología | `elongation_index` | — |
| `nucleus_solidity` | nucleus | `Solidez_convexa` | Morfología | `convex_solidity` | — |
| `mn_elongation` | mn | `MN_Indice_elongacion` | Morfología | `elongation_index` | — |
| `mn_solidity` | mn | `MN_Solidez_convexa` | Morfología | `convex_solidity` | — |
| `perimeter_ratio` | relation | `Razon_perimetros_MN_nucleo` | Relaciones | `mn_nucleus_perimeter_ratio_px` | `mn_nucleus_perimeter_ratio_physical` |
| `mn_separation` | relation | `Separacion_minima_MN_nucleo` | Relaciones | `mn_nucleus_min_distance_px` | `mn_nucleus_min_distance_um` |

---

## Frontend Changes

### `DatasetsView.vue`

- `parseVersion()` and `versionGte()` helpers added (numeric tuple comparison,
  not lexicographic).
- Feature checkboxes filtered by `availableFeatures` computed property:
  only features with `min_version` satisfied by the selected version are shown.
- `versionChanged()` now also removes features from `form.features` that are
  not available for the newly selected version.
- Default `versions` array includes `'2.3'`.

### `characterizationPresentation.js`

- `isSalivaMorphometricV2()` updated to accept `schema_version === '2.3'`.
- `METRIC_LABELS` extended with six 2.3 metric labels.
- `objectMetricGroups()` gains a `schema` parameter. When `schema === '2.3'`,
  adds `elongation_index`, `convex_solidity` to morphology group and
  `mn_nucleus_perimeter_ratio_px`, `mn_nucleus_min_distance_px` to the
  relation group.
- `PHYSICAL_METRICS` extended with 2.3 physical-variant mappings.

### `SalivaMorphometricResult.vue`

- `isExtended` now includes `'2.3'`.
- `hasPhysical` now includes `'2.3'`.
- Physical context section shown for `'2.2'` and `'2.3'`.
- All `SalivaObjectMetrics` calls pass `:schema="resultJson.schema_version"`.

### `SalivaObjectMetrics.vue`

- Accepts new `schema` prop.
- Forwards `schema` to `objectMetricGroups()`.

---

## Files Modified

### Backend

| File | Change |
|---|---|
| `api/services/characterization/geometry.py` | +5 new functions/helpers |
| `api/services/characterization/physical.py` | Added `extend_23_metrics()`, `VERSION_23`, `FEATURE_DIMENSIONS_23`, `PHYSICAL_FIELDS_23` |
| `api/services/characterization/service.py` | Added 2.3 branch in `get_or_create_resultado_caracterizacion()` |
| `api/services/characterization/types.py` | `SALIVA_CHARACTERIZATION_ALGORITHM_VERSION = '2.3'` |
| `api/services/datasets/features.py` | `min_version` on all features; 6 new 2.3 features; empty `UNAVAILABLE`; `SCHEMA_VERSION = 'saliva-nuclear-2'` |
| `api/dataset_views.py` | `'2.3'` in choices; `_parse_version()`; feature-version validation |
| `api/test_characterization_2_3.py` | New: 65 tests (geometry, elongation, version-isolation, object metrics, relation metrics, schema) |
| `api/test_characterization_2_1.py` | +2 regression guard tests |
| `api/test_characterization_2_2.py` | +1 regression guard test; `'2.2'` → `'2.3'` in version assertion |
| `api/test_datasets.py` | +9 new 2.3 Dataset Builder tests |
| `api/tests.py` | `'2.2'` → `'2.3'` in two version assertions |
| `api/test_saliva_strategies.py` | `'2.2'` → `'2.3'` in two version assertions |

### Frontend

| File | Change |
|---|---|
| `src/domain/characterizationPresentation.js` | `isSalivaMorphometricV2` +`'2.3'`; 6 new labels; `objectMetricGroups` schema param; 2.3 `PHYSICAL_METRICS` entries |
| `src/components/characterization/SalivaMorphometricResult.vue` | `isExtended`/`hasPhysical` updated; physical section for 2.3; `:schema` prop on all `SalivaObjectMetrics` |
| `src/components/characterization/SalivaObjectMetrics.vue` | `schema` prop added; forwarded to `objectMetricGroups` |
| `src/views/DatasetsView.vue` | `versionGte`; `availableFeatures`; `versionChanged` update; `'2.3'` in default versions |

### Documentation

| File | Change |
|---|---|
| `AGENTS.md` | Characterization 2.3 updated to "implemented"; MN ↔ nucleus association architecture corrected |
| `docs/95_characterization_23_plan.md` | Implementation overrides applied (elongation from eccentricity; solidity from `area_px2`) |
| `docs/95_characterization_23_feature_gap_closure.md` | This file |

---

## Files NOT Modified (by design)

| File | Reason |
|---|---|
| `api/services/characterization/raster_metrics.py` | Elongation is derived from stored eccentricity — no re-rasterization needed |
| `api/services/characterization/saliva.py` | 2.1 contract is permanent; no 2.3 keys added here |

---

## Preserved Pending Items

- `IMPORTANT_PENDING_18S_A2` — calibration remains PROVISIONAL
- `PENDING_CHARACTERIZATION_22_BACKFILL` — deferred
- `GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING`
- `CAL-OPTIKA-40X-PROVISIONAL-001` remains PROVISIONAL

---

## Test Results

### Backend

```
570 passed, 3 skipped, 0 failed
```

Includes:
- 65 new Characterization 2.3 tests
- 2 new 2.1 regression guards
- 1 new 2.2 regression guard
- 9 new Dataset Builder 2.3 tests
- All pre-existing 493 tests continue to pass

### Frontend

```
229 tests, 224 pass, 5 fail (pre-existing failures, not caused by this sprint)
npm run build: ✓
```

---

## Scientific Decisions Made (authoritative, not to be reopened)

1. **Elongation formula:** `E = 1 − sqrt(1 − eccentricity²)` — derived from
   stored eccentricity; algebraically identical to `1 − b/a`.

2. **Convex Solidity numerator:** existing `area_px2` (not recomputed).

3. **Perimeter ratio physical ≠ pixel** under anisotropic calibration — both
   variants stored separately.

4. **Minimum separation:** true closed-set polygon distance, not centroid
   distance. Returns 0 for touching/overlapping/contained.

5. **Physical minimum distance:** per-coordinate transform first, then distance
   — never `distance_px × average_scale`.

6. **No `raster_metrics.py` changes** — eliminates all risk of eccentricity
   numerical drift.
