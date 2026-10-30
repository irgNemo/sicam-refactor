# Sprint 18U-C1 — Characterization 2.3 Implementation Plan

## Overview

Characterization 2.3 extends the existing 2.2 pipeline with four new metrics that
close the `FEATURE_GAP` identified in Sprint 18U-B and confirmed by the 18U-C0 data
readiness audit. It is strictly additive: every 2.1 and 2.2 result remains
scientifically unchanged.

Scientific definitions are authoritative as specified by the researcher. The
historical Excel is evidence of intent only; 2.3 uses SICAM-coherent definitions.

**In-scope:** backend characterization, physical extension, Dataset Builder feature
catalog, frontend metric display, documentation.

**Out-of-scope:** GLCM changes, BLOOD characterization, calibration promotion, real
data backfill, 2.1/2.2 formula changes.

**Pending preserved items:**
- `IMPORTANT_PENDING_18S_A2`
- `PENDING_CHARACTERIZATION_22_BACKFILL`
- `GLCM_PHYSICAL_DISTANCE_NORMALIZATION = PENDING`

---

## A. Current Architecture Findings

### A.1 Characterization version architecture

SALIVA characterization has two layers:

- **2.1 (pixel):** `saliva.py::characterize_saliva_result()` produces the full
  polygon/raster metric JSON. `SCHEMA_VERSION = '2.1'` is a **permanent constant** in
  `saliva.py` — it identifies the pixel-domain algorithm version and must never change.
- **2.2 (physical extension):** `physical.py::extend_physical_result()` receives the
  2.1 result and adds `*_um` / `*_um2` fields. `VERSION = '2.2'` in `physical.py`
  identifies this layer but is passed as a `version` parameter through the call chain.

`service.py::get_or_create_resultado_caracterizacion()` orchestrates both layers:
1. Calls `get_characterization_algorithm_version(sample_type)` from `types.py` to get
   the **current** algorithm version string.
2. Computes calibration context (with DB lock).
3. Computes fingerprint from segmentation hash + calibration context + **version string**.
4. Queries for existing `ResultadoCaracterizacion` matching version + fingerprint.
5. If none found → runs pixel characterization (always labeled '2.1'), then physical
   extension passing the current version string, then persists with `algorithm_version`.

**Critical discovery:** `characterize_effective_segmentation()` in `service.py`
(lines 95–127) hardcodes `version='2.1'` for the pixel domain:
```python
algorithm_version = ('2.1' if sample_type == SampleType.SALIVA
                     else get_characterization_algorithm_version(sample_type))
```
This means the pixel domain version string is **permanently '2.1'** regardless of the
constant in `types.py`. The constant in `types.py` only affects the outer wrapper
version (`characterization_version` field) and the fingerprint.

### A.2 Version dispatch under the proposed 2.3 architecture

The correct version-aware design is:

```
PIXEL DOMAIN — always '2.1' (saliva.py SCHEMA_VERSION — never changes)
      ↓ characterize_saliva_result()  →  { version: '2.1', schema_version: '2.1', ... }
      ↓
PHYSICAL WRAPPER — version passed as parameter
      ↓ extend_physical_result(pixel_result, effective, context, version='2.2')
      ↓   → sets characterization_version = version ('2.2')
      ↓   → sets schema_version = VERSION ('2.2')  ← BUG: schema_version uses hardcoded constant
      ↓
2.3 EXTENSION — new additive layer
      ↓ extend_23_metrics(physical_result, effective, context, version='2.3')
      ↓   → adds new metric fields, sets characterization_version='2.3', schema_version='2.3'
```

**Issue identified:** In `physical.py` line 128:
```python
result.update(version=version, schema_version=VERSION, characterization_version=version)
```
`schema_version` is set to the module constant `VERSION` (hardcoded `'2.2'`) rather
than the `version` parameter. For clean 2.3 semantics, the 2.3 extension layer must
set `schema_version='2.3'` explicitly.

**Chosen architecture for 2.3 — additive function in `physical.py`:**

Rather than bumping `SALIVA_CHARACTERIZATION_ALGORITHM_VERSION` to `'2.3'` and having
`extend_physical_result()` implicitly produce 2.3 results, introduce a new function:

```
extend_23_metrics(physical_result, effective, context, version='2.3')
```

This function:
1. Receives the already-complete 2.2 result.
2. Adds new 2.3 metric fields to cells/nuclei/micronuclei in-place (deep copy first).
3. Updates `version`, `schema_version`, `characterization_version` to `'2.3'`.
4. Recomputes fingerprint with `version='2.3'`.
5. Updates `provenance` fields.

`service.py` calls the chain:
- `algorithm_version = get_characterization_algorithm_version(sample_type)` → `'2.3'`
- `pixel_result = characterize_effective_segmentation(...)` → `version='2.1'`
- `physical_result = extend_physical_result(..., version='2.2')` → `'2.2'` intermediate
- `final_result = extend_23_metrics(physical_result, ..., version=algorithm_version)` → `'2.3'`

This way, `extend_physical_result()` is **not modified**: it always produces a 2.2
result object. The 2.3 layer is cleanly separate, and bumping the constant cannot
accidentally cause 2.2 calls to emit 2.3 JSON.

**The constant `SALIVA_CHARACTERIZATION_ALGORITHM_VERSION` is changed to `'2.3'`** in
`types.py`. This causes `service.py` to query for / store `algorithm_version='2.3'`
records, correctly bypassing existing 2.2 records.

**Existing 2.2 records:** Remain untouched. The fingerprint includes the version
string, so 2.3 fingerprints are always distinct from 2.2 fingerprints for the same
segmentation data.

**Existing 2.1 records:** Remain untouched (different `algorithm_version`).

### A.3 Storage model

`ResultadoCaracterizacion.resultado_json` is a **JSONField** on the Django model.
There is no separate column per metric. **No migration required for 2.3.**

`algorithm_version` is a plain `CharField`; adding `'2.3'` requires no migration.

### A.4 Geometry helpers (`geometry.py`)

Existing functions reused by the plan:
- `polygon_area(points)` — shoelace formula
- `polygon_perimeter(points)` — Euclidean segment sum
- `polygon_centroid(points)` — geometric centroid
- `polygon_circularity(area, perimeter)` — 4πA/P²
- `is_self_intersecting_polygon(points)` — O(n²) segment check
- `classify_point_in_polygon(point, polygon, epsilon)` — ray casting
- `_segments_intersect(first, second)` — reused by minimum distance

New functions to add:
- `polygon_convex_hull(points)` — Andrew's monotonic chain (see D.2)
- `polygon_convex_hull_area(points)` — calls hull then `polygon_area`
- `minimum_polygon_distance(points_a, points_b)` — closed-set distance (see D.3)

### A.5 Raster/moment helpers (`raster_metrics.py`)

`measure_raster()` computes central moments then:
```
delta = hypot(mu20 − mu02, 2*mu11)
major = (mu20 + mu02 + delta) / 2    ← λ_max
minor = max(0, (mu20 + mu02 − delta) / 2)  ← λ_min
eccentricity = sqrt(max(0, min(1, 1 − minor/major)))
```

**`raster_metrics.py` is NOT modified in Sprint 18U-C1.** See section D.1 for the
override rationale and the eccentricity-based elongation formula.

### A.6 MN ↔ nucleus association semantics (corrected)

The association is **reconstructed deterministically during Characterization**, not
stored in the segmentation payload:

1. `_associate_to_membranes()` assigns each MN to exactly one membrane via
   centroid-in-polygon test.
2. `_nearest_nucleus()` selects, within the MN's membrane, the nucleus with minimum
   Euclidean centroid distance in **pixel space**. Tie-break: lower `id`.
3. The resulting `nucleus_id` is **written into the Characterization JSON** at
   result-build time.

2.3 relationship metrics reuse `nucleus_id` already computed during the same
Characterization pass. They do not independently choose a nucleus.

**Reproducibility:** Deterministic from the polygon data in the effective segmentation.
Re-running characterization on the same effective result always produces the same
association. If the effective segmentation changes (new VALIDADA revision), the
fingerprint changes and a new Characterization is created.

**No change to association semantics is authorized in this sprint.**

### A.7 Dataset Builder feature architecture (current)

- `features.py`: `FEATURES` list dicts have fields: `key`, `entity`, `label`, `group`,
  `pixel`, `physical`. **No version field exists.**
- `dataset_views.py` serializer validates feature keys against the catalog but does
  **not** validate feature–version compatibility beyond the 2.1/PIXELS constraint.
- `builder.py` `metric()` returns `None` for missing paths silently — this is the
  current behavior for unavailable physical metrics in 2.1 datasets.
- Frontend receives the complete feature catalog with no version filtering.

---

## B. Final Metric Contract

### B.1 Elongation Index

| Attribute | Value |
|---|---|
| Internal name | `elongation_index` |
| Human label | `Índice de elongación` |
| Entity scope | nucleus, micronucleus |
| Scientific formula | `E = 1 − sqrt(λ_min / λ_max)` = `1 − b/a` |
| **SICAM 2.3 implementation formula** | **`E = 1 − sqrt(clamp(1 − eccentricity², 0, 1))`** — derived from the existing stored `eccentricity`. No re-rasterization. |
| Derivation | Since `eccentricity = sqrt(1 − λ_min/λ_max)` → `λ_min/λ_max = 1 − eccentricity²` → `E = 1 − sqrt(λ_min/λ_max) = 1 − sqrt(1 − eccentricity²)`. Algebraically identical to the eigenvalue formula. |
| Geometry | Uses the same raster-moment geometry as SICAM eccentricity (guaranteed by derivation). |
| Coordinate space | Pixel coordinates. Dimensionless. No physical variant in this sprint. |
| Units | dimensionless |
| Valid range | `[0, 1]` |
| Null condition | `eccentricity is None` → `elongation_index = None` |
| Degenerate — circle | `eccentricity = 0` → `elongation_index = 0` |
| Degenerate — ideal line | `eccentricity = 1` → `elongation_index = 1` |
| Physical counterpart | none in this sprint |
| Relationship to eccentricity | `eccentricity = sqrt(1 − λ_min/λ_max)`. `elongation_index = 1 − sqrt(λ_min/λ_max)`. Equal at 0 and 1; different for intermediate values. |
| Computed by | `extend_23_metrics()` only — reads `metrics["eccentricity"]` from the 2.2 result |

### B.2 Convex Solidity

| Attribute | Value |
|---|---|
| Internal name | `convex_solidity` |
| Human label | `Solidez convexa` |
| Entity scope | nucleus, micronucleus |
| Formula | `S = area_px2 / polygon_area(convex_hull(points))` |
| Numerator | **Existing `area_px2` from the 2.2 result metrics** — not recomputed |
| Denominator | `polygon_convex_hull_area(points)` — computed from the object's polygon points |
| Geometry | POLYGON |
| Units | dimensionless |
| Valid range | `(0, 1]` — convex object → 1 |
| Null condition | `area_px2` missing or `<= 0`; hull is None (collinear/degenerate); hull area `<= NUMERICAL_EPSILON` |
| Degenerate | explicit null, no silent zero |
| Physical counterpart | none (dimensionless and invariant under uniform affine scale; anisotropic scale changes both numerator and denominator equally) |
| Computed by | `extend_23_metrics()` only — reads `metrics["area_px2"]` and retrieves polygon points from `effective` |

### B.3 MN–Nucleus Perimeter Ratio (pixel)

| Attribute | Value |
|---|---|
| Internal name | `mn_nucleus_perimeter_ratio_px` |
| Human label | `Razón de perímetros MN/núcleo` |
| Entity scope | relation (MN level) |
| Formula | `R_P_px = perimeter_mn_px / perimeter_nucleus_px` |
| Data source | `perimeter_px` already present in both MN and nucleus metrics of the 2.2 result — read directly, no re-computation needed |
| Geometry | POLYGON (pixel coordinates) |
| Units | dimensionless |
| Valid range | `> 0` when defined; typically `<< 1` |
| Null condition | no associated nucleus; nucleus `perimeter_px` = 0 or null; MN `perimeter_px` = null |
| Physical counterpart | `mn_nucleus_perimeter_ratio_physical` (see B.4) |
| Reconstructibility | `mn_nucleus_perimeter_ratio_px = MN_Perimetro_px / Perimetro_px` within float tolerance for the same exported row |
| Multiple MN | one ratio per MN–nucleus association |
| Computed by | `extend_23_metrics()` only — **not** by `characterize_saliva_result()` |

### B.4 MN–Nucleus Perimeter Ratio (physical)

| Attribute | Value |
|---|---|
| Internal name | `mn_nucleus_perimeter_ratio_physical` |
| Human label | `Razón de perímetros MN/núcleo (física)` |
| Formula | `R_P_phys = perimeter_mn_um / perimeter_nucleus_um` |
| Rationale | Under anisotropic calibration `sx ≠ sy`, polygon perimeter transforms non-linearly by geometry/orientation. `R_P_px ≠ R_P_physical` in general. Both values must be computed independently. |
| Geometry | POLYGON (physical coordinates) |
| Units | dimensionless (ratio of physical lengths) |
| Null condition | no physical calibration; or same as pixel null conditions applied to physical perimeters |
| Reconstructibility | `mn_nucleus_perimeter_ratio_physical = MN_Perimetro_um / Perimetro_um` within float tolerance |
| Dataset Builder | PIXELS → `mn_nucleus_perimeter_ratio_px`; PHYSICAL → `mn_nucleus_perimeter_ratio_physical`; BOTH → both distinctly |

**Note on naming:** The suffix `_physical` (not `_um`) is used because the ratio is
dimensionless. The word `_physical` communicates that physical-space perimeters were
used in the calculation.

### B.5 Minimum MN–Nucleus Separation (pixel)

| Attribute | Value |
|---|---|
| Internal name | `mn_nucleus_min_distance_px` |
| Human label | `Separación mínima MN–núcleo` |
| Entity scope | relation (MN level) |
| Definition | Minimum Euclidean distance between the two **closed polygonal sets** (regions, not just boundaries). For disjoint regions: minimum segment-to-segment distance. For regions sharing a boundary point, intersecting, overlapping, or one contained in the other: **0**. |
| Data source | polygon points from `effective['resultado']['objects']` looked up by MN id and `mn['nucleus_id']` |
| Geometry | POLYGON |
| Units | px |
| Valid range | `>= 0`. Value 0 has scientific meaning (contact/overlap/containment). |
| Null condition | no associated nucleus; or either polygon invalid/degenerate |
| Degenerate | non-positive values clamped to 0; never negative |
| Physical counterpart | `mn_nucleus_min_distance_um` |
| Computed by | `extend_23_metrics()` only — **not** by `characterize_saliva_result()` |

### B.6 Minimum MN–Nucleus Separation (physical)

| Attribute | Value |
|---|---|
| Internal name | `mn_nucleus_min_distance_um` |
| Human label | `Separación mínima MN–núcleo (µm)` |
| Formula | Same algorithm as pixel version, applied after coordinate transform: `x_um = x_px * sx`, `y_um = y_px * sy` |
| Units | µm |
| Null condition | same as pixel + no physical calibration available |
| Physical status | PROVISIONAL while `CAL-OPTIKA-40X-PROVISIONAL-001` is PROVISIONAL |
| Anisotropy | must NOT use `distance_px * average_scale`; full per-coordinate transform required before distance calculation |

---

## C. Files to Modify

| File | Purpose | Change |
|---|---|---|
| `api/services/characterization/geometry.py` | Polygon helpers | Add `polygon_convex_hull()`, `polygon_convex_hull_area()`, `minimum_polygon_distance()` and private helpers `_point_to_segment_distance()`, `_segment_to_segment_distance()` |
| `api/services/characterization/raster_metrics.py` | Raster moments | **NOT MODIFIED.** Remains at 2.1 contract. Elongation is derived from stored eccentricity instead. |
| `api/services/characterization/saliva.py` | Main 2.1 pipeline | **NOT MODIFIED for 2.3 output.** `SCHEMA_VERSION` stays `'2.1'`. No 2.3 keys added. |
| `api/services/characterization/physical.py` | 2.2/2.3 physical layer | Add `VERSION_23 = '2.3'`; add `FEATURE_DIMENSIONS_23` and `PHYSICAL_FIELDS_23` dicts; add new function `extend_23_metrics(physical_result, effective, context, version=VERSION_23)`. Elongation reads `metrics["eccentricity"]`; solidity reads `metrics["area_px2"]`. `extend_physical_result()` and `VERSION` are **not modified**. |
| `api/services/characterization/types.py` | Version constant | Change `SALIVA_CHARACTERIZATION_ALGORITHM_VERSION = '2.3'` |
| `api/services/characterization/service.py` | Orchestration | Add `extend_23_metrics()` call branch for `algorithm_version == '2.3'`; pass `version='2.2'` explicitly to `extend_physical_result()` |
| `api/services/datasets/features.py` | Feature catalog | Add `min_version` field to all existing features (`'2.1'` for current, `'2.3'` for new); add new feature dicts; remove four from `UNAVAILABLE`; update `SCHEMA_VERSION` to `'saliva-nuclear-2'` |
| `api/dataset_views.py` | API version list | Add `'2.3'` to versions choice field and options response; add feature–version cross-validation in serializer |
| `api/test_characterization_2_3.py` | New test file | Full test suite for new metrics (see section G) |
| `api/test_characterization_2_1.py` | Existing 2.1 tests | Add regression guard confirming `raster_metrics.py` behavior and eccentricity are unchanged |
| `api/test_characterization_2_2.py` | Existing 2.2 tests | Add regression guard confirming all 2.2 physical outputs are unchanged after 2.3 code addition |
| `api/test_datasets.py` | Dataset Builder tests | Add 2.3 version selection, feature-gating, and new feature path tests |
| `Frontend/src/views/DatasetsView.vue` | Version/feature UI | Update `versionChanged()` for 2.3 (same as 2.2 — all unit modes); filter feature checkboxes by `feature.min_version` |
| `Frontend/src/views/CaracterizacionView.vue` | Metric display | Add display of new metrics for `schema_version === '2.3'` |
| `AGENTS.md` | Project rules | Correct MN ↔ nucleus association description (see section H) |
| `docs/95_characterization_23_feature_gap_closure.md` | Sprint document | Full scientific and implementation documentation (created during implementation) |

---

## D. New Helpers and Refactors

### D.1 Elongation from eccentricity — NO `raster_metrics.py` changes

**OVERRIDE:** `raster_metrics.py` is **not modified** in Sprint 18U-C1. No
`_moment_eigenvalues()` helper is added. `measure_raster()` is not refactored.

**Rationale:** The SICAM eccentricity definition is:
```
eccentricity = sqrt(1 − λ_min / λ_max)
```
Therefore `λ_min / λ_max = 1 − eccentricity²`, and the approved Elongation Index:
```
E = 1 − sqrt(λ_min / λ_max)
  = 1 − sqrt(1 − eccentricity²)
```
is derivable directly from the `eccentricity` already stored in the 2.2 result.
This guarantees the same raster geometry as accepted SICAM eccentricity without
any risk of numerical drift from a second rasterization or from refactoring
`measure_raster()`.

**Implementation in `extend_23_metrics()`:**

```python
ecc = metrics.get('eccentricity')
if ecc is None:
    elongation_index = None
else:
    ratio = max(0.0, min(1.0, 1.0 - ecc * ecc))
    elongation_index = 1.0 - math.sqrt(ratio)
```

Special cases (all handled automatically by the formula):
- `eccentricity = 0` → `elongation_index = 0`
- `eccentricity = 1` → `elongation_index = 1`
- `eccentricity = None` → `elongation_index = None`

Slight floating-point excursions outside `[0, 1]` are clamped by `max(0, min(1, ...))`.

### D.2 Convex hull in `geometry.py`

**Algorithm: Andrew's Monotonic Chain.**

Chosen over Jarvis march because:
- O(n log n) vs O(nh) — faster for large polygons.
- Simpler loop structure; robust handling of collinear points by sort-and-sweep.
- Deterministic output (sorted by x then y → canonical order).
- Well-known, well-tested algorithm.
- No new dependency; pure Python with stdlib `math`.

**Specification:**
```
polygon_convex_hull(points) → list[list[float]] | None
```
- Input: list of `[x, y]` points (same format as all other helpers).
- Returns counter-clockwise hull vertices, or `None` if result has < 3 distinct
  non-collinear points (hull is a line or a point → area = 0).
- Repeated points: deduplicated before sort.
- All collinear: returns `None`.
- Fewer than 3 valid points: returns `None`.
- Numerical tolerance: cross-product comparison uses existing `POINT_BOUNDARY_EPSILON`
  for strict collinearity detection.

```
polygon_convex_hull_area(points) → float | None
```
- Returns `polygon_area(polygon_convex_hull(points))` or `None` if hull is `None`.

### D.3 Minimum polygon distance in `geometry.py`

```
minimum_polygon_distance(points_a, points_b) → float
```

**Definition:** Minimum Euclidean distance between the two closed polygonal **sets**
(filled regions). Returns 0 for any overlap/touching/containment.

**Algorithm:**

1. **Intersection/containment check (short-circuit to 0.0):**
   - If any segment of A intersects any segment of B → return 0.0
     (uses existing `_segments_intersect()`)
   - If any vertex of A is `INSIDE` or `ON_BOUNDARY` of B → return 0.0
     (uses existing `classify_point_in_polygon()`)
   - If any vertex of B is `INSIDE` or `ON_BOUNDARY` of A → return 0.0
   - (Three checks together cover: intersection, partial overlap, full containment.)

2. **Minimum segment-to-segment distance:**
   - For every segment of A paired with every segment of B:
     compute `_segment_to_segment_distance(p1, p2, p3, p4)`
   - Return the minimum.

3. **`_segment_to_segment_distance(p1, p2, p3, p4)` (private helper):**
   - Computes minimum of:
     - point_to_segment_distance(p1, p3, p4)
     - point_to_segment_distance(p2, p3, p4)
     - point_to_segment_distance(p3, p1, p2)
     - point_to_segment_distance(p4, p1, p2)
   - Handles projection clamping: if the foot of perpendicular falls outside the
     segment, use the nearer endpoint.
   - Always returns `>= 0`.

4. **`_point_to_segment_distance(p, a, b)` (private helper):**
   - Projects `p` onto segment `ab`, clamps to `[0, 1]`.
   - Returns Euclidean distance from `p` to the clamped projection.

**Return value:** Always `>= 0`. Value 0 is exact (not epsilon-clamped).

**Unit agnosticism:** The function operates on whatever coordinate units are passed.
For physical distances, callers transform coordinates first:
```python
def _physical_points(points, sx, sy):
    return [[x * sx, y * sy] for x, y in points]
```
This avoids duplicate geometric algorithms for pixel and physical space.

### D.4 Service.py orchestration for 2.3

In `get_or_create_resultado_caracterizacion()`, add a branch after the physical
extension:

```python
pixel_result = characterize_effective_segmentation(...)      # version='2.1'
physical_result = extend_physical_result(                    # version='2.2' (intermediate)
    pixel_result, effective, context, version='2.2'
) if context is not None else pixel_result

if algorithm_version == '2.3':
    resultado_json = extend_23_metrics(
        physical_result, effective, context, algorithm_version
    )
elif algorithm_version == '2.2':
    resultado_json = physical_result
else:
    resultado_json = pixel_result
```

This preserves full 2.2 behavior when the version constant is `'2.2'`, and activates
2.3 cleanly when the constant is `'2.3'`. Future versions would add new `elif` branches.

**`extend_23_metrics()` in `physical.py` — full responsibility:**

This function is the **sole producer of all six 2.3 metrics**. It:

1. Starts with `copy.deepcopy(physical_result)` — never mutates its input.
2. Builds `points_by_id` from `effective['resultado']['objects']` (same as
   `extend_physical_result()`).
3. For each nucleus and MN in `cells`, `unassociated`, `ambiguous`:
   - **Elongation:** Reads `metrics["eccentricity"]` from the existing 2.2 result.
     Computes `elongation_index = 1 − sqrt(clamp(1 − ecc², 0, 1))`.
     No rasterization, no moment recomputation.
   - **Convex Solidity:** Reads `metrics["area_px2"]` from the existing 2.2 result.
     Looks up polygon points by `object_id` from `points_by_id`.
     Calls `polygon_convex_hull_area(points)` → hull area.
     Computes `convex_solidity = area_px2 / hull_area`.
   - Sets both in `item['metrics']`.
4. For each MN in `cells`, `unassociated`, `ambiguous`:
   - Reads `mn['nucleus_id']` from the result.
   - **Pixel perimeter ratio:** Reads `mn['metrics']['perimeter_px']` and nucleus
     `perimeter_px` from the result. Computes `mn_nucleus_perimeter_ratio_px`.
   - **Physical perimeter ratio:** Reads `mn['metrics']['perimeter_um']` and nucleus
     `perimeter_um` from the result. Computes `mn_nucleus_perimeter_ratio_physical`.
   - **Pixel min distance:** Looks up MN polygon and nucleus polygon from `points_by_id`.
     Calls `minimum_polygon_distance(mn_points, nucleus_points)` →
     `mn_nucleus_min_distance_px`.
   - **Physical min distance:** Transforms each polygon's coordinates
     (`x_um = x_px * sx`, `y_um = y_px * sy`), calls `minimum_polygon_distance`
     again → `mn_nucleus_min_distance_um`.
   - Sets all four relation metrics in `mn['metrics']`.
5. Resets `version`, `schema_version`, `characterization_version` to `VERSION_23`.
6. Recomputes `provenance.fingerprint` with `version=VERSION_23`.

Unassociated MN (no `nucleus_id`): all four relation metrics → `None`.

### D.5 New FEATURE_DIMENSIONS and PHYSICAL_FIELDS entries

In `physical.py` (added, not modifying existing entries):

```python
# Additional entries for 2.3 — in a separate section for clarity
FEATURE_DIMENSIONS_23 = {
    'elongation_index': 'DIMENSIONLESS',
    'convex_solidity': 'DIMENSIONLESS',
    'mn_nucleus_perimeter_ratio_px': 'DIMENSIONLESS',
    'mn_nucleus_perimeter_ratio_physical': 'DIMENSIONLESS',
    'mn_nucleus_min_distance_px': 'LENGTH',
}

PHYSICAL_FIELDS_23 = {
    'mn_nucleus_min_distance_px': 'mn_nucleus_min_distance_um',
}
```

These are used only by `extend_23_metrics()` and do not modify the 2.2 dictionaries.

---

## E. Persistence / Version Plan

### E.1 Version strings

| Constant | Location | New value | Notes |
|---|---|---|---|
| `SALIVA_CHARACTERIZATION_ALGORITHM_VERSION` | `types.py` | `'2.3'` | Single point of dispatch |
| `SCHEMA_VERSION` | `saliva.py` | stays `'2.1'` | Permanent pixel-domain label |
| `VERSION` | `physical.py` | stays `'2.2'` | 2.2 layer identity, not changed |
| New constant `VERSION_23` | `physical.py` | `'2.3'` | Used by `extend_23_metrics()` |

The stored JSON will contain `version='2.3'`, `schema_version='2.3'`,
`characterization_version='2.3'`, `provenance.pixel_algorithm_version='2.1'`.

### E.2 Fingerprint

`fingerprint()` receives `version` as a parameter. Since `extend_23_metrics()` calls
`fingerprint(..., version='2.3')`, the hash includes `'2.3'` and is always distinct
from any 2.2 fingerprint, even for identical segmentation and calibration data.

### E.3 Migration

**NO MIGRATION REQUIRED.** `resultado_json` is a JSONField. `algorithm_version` is a
plain CharField. The serializer `ChoiceField` for `characterization_version` in
`dataset_views.py` is a validation rule, not a DB constraint.

---

## F. Dataset Builder Plan

### F.1 Feature–version gating design

**Approach: `min_version` field added to each feature dict.**

Each feature in `features.py` gains a `min_version` string field:
- Existing features: `min_version='2.1'`
- New 2.3 features: `min_version='2.3'`

**Backend enforcement (authoritative):**

Version comparison must NOT rely on lexicographic string ordering (e.g.,
`'2.10' < '2.3'` would be incorrect). Use dotted-numeric tuple comparison.

Add a utility function in `dataset_views.py` (or a shared utilities module):

```python
def _parse_version(v):
    """Parse '2.3' → (2, 3); raises ValueError for malformed strings."""
    return tuple(int(part) for part in v.split('.'))
```

In the serializer `validate()`:

```python
requested_ver = _parse_version(data['characterization_version'])
for feature_key in data['features']:
    feature = next((f for f in FEATURES if f['key'] == feature_key), None)
    if feature:
        required_ver = _parse_version(feature['min_version'])
        if requested_ver < required_ver:
            raise ValidationError(
                f"La característica '{feature_key}' requiere versión "
                f"{feature['min_version']} o superior."
            )
```

This is safe for `'2.10'`, `'3.0'`, etc.

**Frontend enforcement (UX only, not authoritative):**

The backend `options` response includes `min_version` as a string for each feature.
The frontend must not do raw string comparison. Use numeric tuple parsing in
JavaScript:

```javascript
function parseVersion(v) {
    return v.split('.').map(Number);
}
function versionGte(a, b) {
    const pa = parseVersion(a), pb = parseVersion(b);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
        const ai = pa[i] ?? 0, bi = pb[i] ?? 0;
        if (ai !== bi) return ai > bi;
    }
    return true;
}
```

Filter feature checkboxes:

```javascript
availableFeatures(group) {
    return this.options.features.filter(f =>
        f.group === group &&
        versionGte(this.form.characterization_version, f.min_version)
    );
}
```

2.3 features are hidden for 2.1/2.2 selections. Backend rejects regardless.

**Options endpoint update:** Pass `min_version` through to the frontend in the
`/api/datasets/options/` response (already included since `FEATURES` dicts are
serialized directly).

### F.2 New feature definitions in `features.py`

Schema version bumped to `SCHEMA_VERSION = 'saliva-nuclear-2'` to distinguish from
the current `'saliva-nuclear-1'`.

New entries (appended after existing features, preserving catalog order):

| key | entity | label | group | pixel path | physical path | min_version |
|---|---|---|---|---|---|---|
| `nucleus_elongation` | nucleus | `Indice_elongacion` | Morfología | `elongation_index` | `None` | `'2.3'` |
| `nucleus_solidity` | nucleus | `Solidez_convexa` | Morfología | `convex_solidity` | `None` | `'2.3'` |
| `mn_elongation` | mn | `MN_Indice_elongacion` | Morfología | `elongation_index` | `None` | `'2.3'` |
| `mn_solidity` | mn | `MN_Solidez_convexa` | Morfología | `convex_solidity` | `None` | `'2.3'` |
| `perimeter_ratio` | relation | `Razon_perimetros_MN_nucleo` | Relaciones | `mn_nucleus_perimeter_ratio_px` | `mn_nucleus_perimeter_ratio_physical` | `'2.3'` |
| `mn_separation` | relation | `Separacion_minima_MN_nucleo` | Relaciones | `mn_nucleus_min_distance_px` | `mn_nucleus_min_distance_um` | `'2.3'` |

Remove the four entries from `UNAVAILABLE`.

### F.3 Dataset Builder units semantics for new features

| Feature | PIXELS | PHYSICAL | BOTH |
|---|---|---|---|
| `nucleus_elongation` / `mn_elongation` | pixel path (only) | pixel path (no physical variant) | pixel path (only) |
| `nucleus_solidity` / `mn_solidity` | pixel path (only) | pixel path (only) | pixel path (only) |
| `perimeter_ratio` | `mn_nucleus_perimeter_ratio_px` | `mn_nucleus_perimeter_ratio_physical` | both columns |
| `mn_separation` | `mn_nucleus_min_distance_px` | `mn_nucleus_min_distance_um` | both columns |

The existing `columns()` function handles `physical=None` features correctly (no
physical column generated). No change to `columns()` logic needed.

### F.4 Export reconstructibility

Pixel perimeter ratio reconstructibility:
```
Razon_perimetros_MN_nucleo_px  ×  Perimetro_px  ==  MN_Perimetro_px
```
(within floating-point tolerance, using values from the same exported row).

Physical perimeter ratio reconstructibility:
```
Razon_perimetros_MN_nucleo_phys  ×  Perimetro_um  ==  MN_Perimetro_um
```

---

## G. Test Matrix

### G.1 New file: `test_characterization_2_3.py`

#### Geometry — convex hull (pure unit tests)

| Test | Assertion |
|---|---|
| `test_convex_hull_triangle` | 3-point triangle → hull identical to input |
| `test_convex_hull_square_with_interior_point` | Square + 1 interior point → hull = square 4 points |
| `test_convex_hull_concave_l_shape` | L-shape → hull area > polygon area |
| `test_convex_hull_collinear_returns_none` | All collinear points → None |
| `test_convex_hull_duplicate_points_ok` | Repeated vertices → deduplicated; result valid |
| `test_convex_hull_fewer_than_3_returns_none` | 2 points → None |
| `test_convex_hull_area_convex_polygon_equals_area` | Convex polygon → hull area == polygon area |
| `test_convex_solidity_square_is_1` | Square → solidity = 1.0 |
| `test_convex_solidity_concave_less_than_1` | L-shape → 0 < solidity < 1 |
| `test_convex_solidity_null_for_collinear` | Collinear → null |
| `test_convex_solidity_null_for_two_points` | < 3 points → null |

#### Geometry — minimum polygon distance (pure unit tests)

| Test | Assertion |
|---|---|
| `test_min_dist_separated_horizontal` | Two rect boxes, gap=5 → exactly 5.0 |
| `test_min_dist_separated_vertical` | Two rect boxes, gap=3 → exactly 3.0 |
| `test_min_dist_diagonal` | Known diagonal separation → exact Euclidean value |
| `test_min_dist_nearest_point_inside_edge_not_vertex` | Nearest point lies on a segment interior → value less than any vertex-to-vertex distance |
| `test_min_dist_touching` | Shared corner point → 0.0 |
| `test_min_dist_shared_edge` | Overlapping edge → 0.0 |
| `test_min_dist_partial_intersection` | Crossing segments → 0.0 |
| `test_min_dist_full_containment` | Inner polygon inside outer → 0.0 |
| `test_min_dist_identical_polygons` | Same polygon → 0.0 |
| `test_min_dist_anisotropic_physical_ne_px_times_avg_scale` | Transform then distance ≠ px_distance * (sx+sy)/2 |

#### Elongation index — pure unit tests (eccentricity-based transformation)

| Test | Assertion |
|---|---|
| `test_elongation_ecc_zero_is_zero` | `eccentricity = 0` → `elongation_index = 0` |
| `test_elongation_ecc_one_is_one` | `eccentricity = 1` → `elongation_index = 1` |
| `test_elongation_ecc_point6` | `eccentricity = 0.6` → `elongation_index = 1 − sqrt(1 − 0.36) = 0.2` (exact) |
| `test_elongation_ecc_none_is_none` | `eccentricity = None` → `elongation_index = None` |
| `test_elongation_not_equal_eccentricity` | For `eccentricity = 0.6`: `elongation_index = 0.2 ≠ 0.6` |
| `test_elongation_clamp_fp_excursion` | Slightly negative `1 − ecc²` due to float rounding → clamped to 0, elongation → 1 (not NaN/error) |
| `test_elongation_range_0_to_1` | 20 distinct eccentricity values in [0, 1] → all elongation values in [0, 1] |
| `test_elongation_formula_verified` | For `ecc = 0.8`: `elongation = 1 − sqrt(1 − 0.64) = 1 − 0.6 = 0.4`. Numerically exact. |

#### Version-isolation tests (critical)

| Test | Assertion |
|---|---|
| `test_2_1_output_has_no_2_3_keys` | `characterize_saliva_result()` output for nucleus metrics contains none of: `elongation_index`, `convex_solidity`. MN metrics contain none of: `mn_nucleus_perimeter_ratio_px`, `mn_nucleus_min_distance_px`. |
| `test_2_2_output_has_no_2_3_keys` | `extend_physical_result()` output (with physical context) adds no 2.3 keys — same assertion as above |
| `test_2_3_output_has_all_new_keys` | `extend_23_metrics()` output contains all six keys for a valid nucleus/MN pair |
| `test_2_1_json_identical_after_23_code` | Run 2.1 characterization with deterministic fixture — JSON is identical after all 2.3 code is added (no raster_metrics.py change → no risk of drift) |
| `test_2_2_json_identical_after_23_code` | Same for 2.2 — JSON is identical after all 2.3 code is added |
| `test_raster_metrics_behavior_unchanged` | Existing eccentricity value for known fixture remains unchanged — asserted after all 2.3 code is in place |

#### Object-level metrics in full characterization

| Test | Assertion |
|---|---|
| `test_nucleus_2_3_has_elongation_and_solidity` | Nucleus with valid polygon and non-null eccentricity → both non-null in 2.3 result |
| `test_mn_2_3_has_elongation_and_solidity` | MN with valid polygon and non-null eccentricity → both non-null |
| `test_elongation_null_when_eccentricity_null` | Object with `eccentricity = null` in 2.2 result → elongation null in 2.3 result |
| `test_convex_solidity_null_for_collinear` | Collinear polygon → solidity null |
| `test_convex_solidity_reconstructible` | `convex_solidity * convex_hull_area_px2 ≈ area_px2` within float tolerance |

#### Relation metrics in full characterization

| Test | Assertion |
|---|---|
| `test_perimeter_ratio_px_exact` | Known polygon pair: ratio = perimeter_mn / perimeter_nucleus exactly |
| `test_perimeter_ratio_px_null_no_nucleus` | Unassociated MN → null |
| `test_perimeter_ratio_px_null_zero_perimeter` | Degenerate nucleus → null |
| `test_perimeter_ratio_multiple_mn` | 3 MN → 3 independent ratios |
| `test_perimeter_ratio_px_reconstructible` | `ratio * nucleus_perimeter == mn_perimeter` within tolerance |
| `test_perimeter_ratio_physical_ne_px` | Anisotropic calibration: physical ratio ≠ pixel ratio |
| `test_perimeter_ratio_physical_reconstructible` | `ratio_phys * perimeter_um == mn_perimeter_um` within tolerance |
| `test_min_dist_px_exact` | Known separated polygons → exact pixel distance |
| `test_min_dist_px_zero_touching` | Touching polygons → 0 |
| `test_min_dist_px_zero_contained` | MN inside nucleus polygon → 0 |
| `test_min_dist_px_null_no_nucleus` | Unassociated MN → null |
| `test_min_dist_um_anisotropic` | Physical distance computed with per-coord transform |
| `test_min_dist_um_null_no_calibration` | No series → mn_nucleus_min_distance_um null |
| `test_min_dist_um_provisional` | PROVISIONAL calibration → distance computed, status PROVISIONAL in context |

#### Schema, version, fingerprint

| Test | Assertion |
|---|---|
| `test_schema_version_is_2_3` | Result JSON has `version='2.3'`, `schema_version='2.3'` |
| `test_pixel_algorithm_version_still_2_1` | `provenance.pixel_algorithm_version='2.1'` |
| `test_fingerprint_distinct_from_2_2` | Same segmentation + calibration → 2.3 fingerprint ≠ 2.2 fingerprint |
| `test_version_dispatch_2_2_still_works` | When constant reverted to `'2.2'`, result has no 2.3 fields |

#### Dataset Builder tests (in `test_datasets.py`)

| Test | Assertion |
|---|---|
| `test_version_2_3_selectable` | `'2.3'` in options `versions` list |
| `test_2_3_feature_rejected_for_2_1` | Submit `nucleus_elongation` with version `'2.1'` → 400 error |
| `test_2_3_feature_rejected_for_2_2` | Submit `nucleus_elongation` with version `'2.2'` → 400 error |
| `test_2_3_features_accepted_for_2_3` | All new feature keys accepted with version `'2.3'` |
| `test_min_version_in_options_response` | Options response includes `min_version` for each feature |
| `test_perimeter_ratio_reconstructible_from_export` | Exported ratio equals exported perimeters ratio |

### G.2 Regression tests (explicit additions to existing files)

In `test_characterization_2_1.py`, add:
- `test_eccentricity_exact_value_unchanged_after_23_refactor`: use the existing
  rectangle fixture, assert exact float equality to the pre-refactor expected value.

In `test_characterization_2_2.py`, add:
- `test_physical_outputs_unchanged_after_23_code_addition`: run 2.2 characterization
  with known fixture, assert all existing 2.2 fields are byte-identical to expectations.

---

## H. AGENTS.md Correction

**Current incorrect text** (in "Non-obvious architectural constraints"):

> **current persisted MN ↔ nucleus association mechanism is identified.**

The word "persisted" is incorrect in the context of the current implementation.

**Proposed corrected wording** for the relevant AGENTS.md section (under
"Non-obvious architectural constraints"):

> **MN ↔ nucleus association is reconstructed deterministically during
> Characterization, not persisted in the segmentation payload.** Within each
> membrane's context, the MN is assigned to the nearest nucleus by Euclidean
> centroid distance in pixel space, with tie-breaking by lower object ID. The
> resulting `nucleus_id` is written into the Characterization JSON. All 2.3
> relational metrics must use this same association computed during the same
> Characterization pass — they must not independently select a nucleus.

The existing rule line `**current persisted MN ↔ nucleus association mechanism is identified.**` in the audit report task description should be understood as referring to the *current characterization-time* assignment (not a segmentation-level persisted value). The AGENTS.md update clarifies this for all future agents.

---

## I. Scientific Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| 2.1 contract contaminated by 2.3 keys if `saliva.py` is mistakenly changed | CRITICAL | `saliva.py` has zero 2.3 changes; version-isolation tests assert key absence in 2.1/2.2 output |
| `measure_raster()` public output altered by `_moment_eigenvalues()` refactor | HIGH | `measure_raster()` return dict is unchanged; `_moment_eigenvalues` is private and only called internally; explicit 2.1 regression test confirms JSON byte-identity |
| Eccentricity numerical drift after `_moment_eigenvalues()` refactor | HIGH | Arithmetic is algebraically identical; existing fixture test asserts exact float equality |
| Re-rasterization in `extend_23_metrics()` diverges from 2.1 rasterization | MEDIUM | Uses the same `rasterize_object()` call with `grayscale_image=None`; the 2.1 pass also uses `None` when image unavailable; deterministic |
| Convex hull correctness on non-convex polygons | MEDIUM | Andrew monotonic chain is well-defined; test with L-shape, star, degenerate cases |
| `minimum_polygon_distance` returning non-zero for contained polygons | HIGH | Explicit containment test; `classify_point_in_polygon()` check fires before segment loop |
| Anisotropic physical distance using average scale | HIGH | Architecture forces per-coordinate transform; same `physical_distance()` reference pattern |
| `extend_physical_result()` accidentally modified | HIGH | 2.3 layer is a new separate function; `extend_physical_result()` and `VERSION` are untouched |
| 2.2 characterization accidentally producing 2.3 JSON | HIGH | `service.py` branch: `extend_23_metrics()` only when `algorithm_version == '2.3'` |
| Perimeter ratio physical ≠ pixel not caught | MEDIUM | Explicit test asserting inequality under anisotropic calibration |
| Feature-gating via lexicographic string comparison fails for 2.10+ | MEDIUM | `_parse_version()` / `versionGte()` used in both backend and frontend |
| Feature-gating backend not authoritative | MEDIUM | Serializer `validate()` rejects invalid version–feature combinations before any DB write |
| `IMPORTANT_PENDING_18S_A2` — physical values scientifically provisional | ACKNOWLEDGED | Preserved in provenance; not promoted in this sprint |

**No remaining open scientific decisions.** All four metric definitions are
authoritatively specified. Elongation formula confirmed as `1 − b/a = 1 − sqrt(λ_min/λ_max)`.
Line-like degenerate → elongation = 1 (not null). Version isolation is enforced by architecture.

---

## J. Implementation Sequence

```
Step 1.  geometry.py
         Add polygon_convex_hull(), polygon_convex_hull_area()
         Add _point_to_segment_distance(), _segment_to_segment_distance()
         Add minimum_polygon_distance()
         [Pure functions; testable in isolation]

Step 2.  physical.py — SKIP raster_metrics.py and saliva.py
         [raster_metrics.py is NOT modified — elongation derived from stored eccentricity]
         [saliva.py is NOT modified for 2.3 output fields]
         Add VERSION_23 = '2.3'
         Add FEATURE_DIMENSIONS_23 and PHYSICAL_FIELDS_23
         Add extend_23_metrics() function (computes ALL six 2.3 metrics):
           - elongation: reads metrics["eccentricity"], computes 1-sqrt(clamp(1-ecc²,0,1))
           - convex_solidity: reads metrics["area_px2"], calls polygon_convex_hull_area(points)
           - perimeter ratios: reads stored perimeter_px / perimeter_um directly
           - min distances: calls minimum_polygon_distance(); physical uses per-coord transform
         Import polygon_convex_hull_area and minimum_polygon_distance from geometry

Step 5.  service.py
         Add extend_23_metrics() call branch for algorithm_version == '2.3'
         Pass version='2.2' explicitly to extend_physical_result()
         [saliva.py and extend_physical_result() NOT modified]

Step 6.  types.py
         Bump SALIVA_CHARACTERIZATION_ALGORITHM_VERSION = '2.3'

Step 7.  test_characterization_2_3.py
         Create and run all targeted tests
         [Steps 1–6 must be stable before this step]

Step 8.  Run full backend regression:
         python -m pytest -q (from apps/web/Backend)
         Confirm: all previously passing tests still pass

Step 9.  dataset_views.py
         Add '2.3' to ChoiceField and options response
         Add feature–min_version cross-validation to serializer

Step 10. features.py
         Add min_version to all existing features
         Add new 2.3 feature dicts
         Remove four from UNAVAILABLE
         Bump SCHEMA_VERSION

Step 11. test_datasets.py
         Add 2.3 version and feature-gating tests

Step 12. Frontend: DatasetsView.vue
         Update versionChanged() for 2.3
         Add min_version filtering to feature checkboxes

Step 13. Frontend: CaracterizacionView.vue
         Add 2.3 metric display for new fields

Step 14. Full frontend tests + npm run build

Step 15. AGENTS.md correction (MN association wording)

Step 16. docs/95_characterization_23_feature_gap_closure.md (sprint doc)

Step 17. Final: git status, git diff --check, DB integrity verification
```

Steps 1–2 may run in one pass (geometry helpers + physical.py extension). Steps 3–5
are service plumbing. Steps 6–7 validate. Steps 8–10 are Dataset Builder. Steps 11–13
are frontend. Steps 14–16 are documentation and verification.

---

## K. Acceptance Criteria

### Version isolation (critical)
- [ ] `characterize_saliva_result()` output contains none of the six 2.3 metric keys
- [ ] `extend_physical_result()` output contains none of the six 2.3 metric keys
- [ ] `extend_23_metrics()` output contains all six new metric keys
- [ ] JSON output from 2.1 characterization is byte-identical before and after 2.3 code addition
- [ ] JSON output from 2.2 characterization is byte-identical before and after 2.3 code addition

### Scientific correctness
- [ ] `elongation_index = 0` for `eccentricity = 0`
- [ ] `elongation_index = 1` for `eccentricity = 1`
- [ ] `elongation_index ≠ eccentricity` for intermediate values
- [ ] `elongation_index = 1 − sqrt(1 − ecc²)` numerically verified for known ecc values
- [ ] `elongation_index = null` when `eccentricity = null`
- [ ] `convex_solidity = 1.0` for a square polygon
- [ ] `convex_solidity < 1.0` for a concave polygon; exact value verifiable
- [ ] `mn_nucleus_perimeter_ratio_px = perimeter_mn / perimeter_nucleus` (float tolerance)
- [ ] `mn_nucleus_perimeter_ratio_physical = perimeter_mn_um / perimeter_nucleus_um` (float tolerance)
- [ ] Pixel and physical perimeter ratios are NOT equal under anisotropic calibration
- [ ] `mn_nucleus_min_distance_px = 0` for touching, intersecting, and contained cases
- [ ] `mn_nucleus_min_distance_px > 0` for separated polygons; exact value matches geometry
- [ ] Physical distance uses per-coordinate transform, not average scale
- [ ] `mn_nucleus_min_distance_px = 0` when MN polygon is fully inside nucleus polygon

### Regression
- [ ] `raster_metrics.py` is unchanged — no modification to `measure_raster()` or any helper
- [ ] Existing eccentricity test value identical after 2.3 code added (no rasterization touched)
- [ ] All previously passing backend tests still pass
- [ ] All previously passing frontend tests still pass
- [ ] `makemigrations --check` → No changes detected

### Versioning
- [ ] New characterization JSON has `version='2.3'`, `schema_version='2.3'`
- [ ] `provenance.pixel_algorithm_version = '2.1'`
- [ ] Fingerprint for same segmentation + calibration differs from 2.2
- [ ] Existing 2.1 records untouched (different `algorithm_version`)
- [ ] Existing 2.2 records untouched (different fingerprint)
- [ ] When version constant hypothetically set back to `'2.2'`, characterization produces no 2.3 fields

### Dataset Builder
- [ ] Version `'2.3'` appears in options `versions` list
- [ ] 2.3-only feature submitted with version `'2.1'` or `'2.2'` → 400 validation error
- [ ] 2.3 features accepted for version `'2.3'`
- [ ] `Razon_perimetros_MN_nucleo_px × Perimetro_px = MN_Perimetro_px` (float tolerance)
- [ ] `Razon_perimetros_MN_nucleo_phys × Perimetro_um = MN_Perimetro_um` (float tolerance)
- [ ] Frontend hides 2.3 features when version `'2.1'` or `'2.2'` is selected

### Data safety
- [ ] `manage.py check` clean
- [ ] `npm run build` PASS
- [ ] DB integrity_check = ok
- [ ] foreign_key_check = []
- [ ] SHA-256 of all real data tables identical before/after
- [ ] 95 media files unchanged
- [ ] No real characterization run on real samples

---

## L. Git State

This plan document is `docs/95_characterization_23_plan.md`.

No production code, tests, migrations, database, or media were modified during
planning.

Expected `git status --short`:
```
?? docs/95_characterization_23_plan.md
```

`git diff --check`: PASS.
