# 07 - Current Domain Model

## Current Model Diagram

```mermaid
erDiagram
    Paciente ||--o{ Caso : has
    Paciente ||--o{ AnalisisPred : has
    Caso ||--o{ AnalisisPred : has
    AnalisisPred ||--o{ MuestraSaliva : has
    MuestraSaliva ||--o{ ResultadoAnalisis : has
    ResultadoAnalisis ||--o{ AnalisisMascara : has

    Paciente {
        int id_paciente PK
        string nombre
        string apellido
        date fecha_nacimiento
        string identificacion UK
        string email
        string telefono
        datetime fecha_registro
    }

    Caso {
        int id_caso PK
        int paciente FK
        string titulo
        text descripcion
        datetime fecha_creacion
    }

    AnalisisPred {
        int id_analisis PK
        int id_paciente_fk FK
        int id_caso_fk FK
        date fecha
        int estado
        text observaciones
    }

    MuestraSaliva {
        int id_muestra PK
        int analisis FK
        image imagen
        datetime fecha_subida
    }

    ResultadoAnalisis {
        int id_resultado PK
        int muestra FK
        int nucleos
        int micronucleos
        int membranas
        datetime fecha_analisis
    }

    AnalisisMascara {
        int id_mascara_analisis PK
        int resultado FK
        string tipo_mascara
        image imagen
        string algoritmo
        datetime fecha_generacion
    }
```

## Current Domain Interpretation

### Patient

Represents the person associated with clinical/cytological studies.

Current model: `Paciente`.

### Case

Represents a clinical case or study container for a patient.

Current model: `Caso`.

### Analysis

Represents a processing/review workflow within a case.

Current model: `AnalisisPred`.

### Sample Image

Currently limited to saliva.

Current model: `MuestraSaliva`.

### Segmentation Result

Currently represented only as aggregate counts in `ResultadoAnalisis` and mask image files in `AnalisisMascara`.

### Characterization Result

Not yet modeled.

### Report

Not yet modeled.

## Domain Issues

### Issue 1: Analysis duplicates patient relationship

`AnalisisPred` links both to `Paciente` and `Caso`.

Since `Caso` already belongs to `Paciente`, this creates possible inconsistency:

```text
AnalisisPred.id_paciente_fk != AnalisisPred.id_caso_fk.paciente
```

Recommendation: make `Analysis` depend only on `Case`, or enforce validation.

### Issue 2: Sample type is not general

Current model:

```text
MuestraSaliva
```

Required domain:

```text
SampleImage
- type: SALIVA | BLOOD
```

### Issue 3: Segmentation polygons are not persisted

The microservices return object polygons, but the backend currently has no JSON field to store them.

### Issue 4: Manual validation is not represented

The documents describe specialist validation/editing. Current models do not represent:

- draft segmentation
- edited segmentation
- validated segmentation
- reviewer
- validation date

### Issue 5: Characterization is absent

The code does not yet model:

- area
- perimeter
- circularity
- centroid
- intensity
- nucleus-micronucleus relation

## Proposed Target Domain Model

```mermaid
erDiagram
    User ||--o| Doctor : profile
    Doctor ||--o{ ClinicalCase : owns
    Patient ||--o{ ClinicalCase : has
    ClinicalCase ||--o{ Analysis : has
    Analysis ||--o{ SampleImage : has
    SampleImage ||--o{ SegmentationResult : has
    SegmentationResult ||--o{ SegmentedObject : has
    SegmentationResult ||--o| CharacterizationResult : produces
    ClinicalCase ||--o{ Report : has

    User {
        int id PK
        string email
        string password_hash
        bool is_active
    }

    Doctor {
        int id PK
        int user_id FK
        string license_number
        string specialty
        string institution
    }

    Patient {
        int id PK
        string first_name
        string last_name
        string external_identifier UK
        date birth_date
    }

    ClinicalCase {
        int id PK
        int patient_id FK
        int doctor_id FK
        string title
        text description
        string status
        datetime created_at
    }

    Analysis {
        int id PK
        int case_id FK
        string status
        text observations
        datetime created_at
    }

    SampleImage {
        int id PK
        int analysis_id FK
        string sample_type
        image file
        string processing_status
        datetime uploaded_at
    }

    SegmentationResult {
        int id PK
        int sample_image_id FK
        string algorithm
        string status
        json objects_json
        json counts_json
        bool is_validated
        datetime created_at
        datetime validated_at
    }

    SegmentedObject {
        int id PK
        int segmentation_id FK
        string object_type
        int source_object_id
        json polygon
        json metrics_json
    }

    CharacterizationResult {
        int id PK
        int segmentation_id FK
        json metrics_json
        datetime created_at
    }

    Report {
        int id PK
        int case_id FK
        string report_type
        file file
        datetime generated_at
    }
```

## Minimal Migration Strategy

To avoid breaking the current code immediately:

1. Add `tipo_muestra` to samples or introduce `ImagenMuestra`.
2. Add `ResultadoSegmentacion` with JSON fields.
3. Keep `ResultadoAnalisis` temporarily for legacy count display.
4. Refactor frontend to consume the new result contract.
5. Migrate data from `MuestraSaliva` to `ImagenMuestra` if needed.
