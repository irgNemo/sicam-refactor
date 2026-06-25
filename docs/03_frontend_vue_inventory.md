# 03 - Vue Frontend Inventory

## Project

```text
micronucleos-web/Frontend
```

## Frameworks and Libraries

- Vue 3
- Vite
- Axios
- ESLint

## Main Files

```text
src/main.js
src/App.vue
src/components/TopBar.vue
src/components/SideBar.vue
src/components/MainContent.vue
src/views/RegistroView.vue
```

## Package Scripts

```json
{
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "lint": "eslint . --fix --cache"
}
```

## Main Application Layout

`App.vue` controls the active section using local component state:

```text
seccion: "segmentacion"
```

Detected sections:

```text
segmentacion
analisis
caracterizacion
registro
```

Current status:

- `segmentacion`: active UI shell
- `registro`: implemented
- `analisis`: placeholder
- `caracterizacion`: placeholder

## Component: TopBar.vue

Purpose: main navigation between sections.

Observed behavior:

- Emits `change-section`
- Parent `App.vue` switches active section

## Component: SideBar.vue

Purpose: search/select patients and cases.

### Backend calls

```http
GET /api/pacientes/
GET /api/casos/
GET /api/analisis/
```

### Local state

```text
pacientes
casos
analisis
busquedaPaciente
pacientesFiltrados
pacienteSeleccionado
casoSeleccionado
resumen
```

### Emits

```text
select-patient
select-case
```

### Current behavior

- Loads patients, cases and analyses in parallel.
- Filters patients client-side by name, surname or identification.
- Builds patient cases by joining frontend arrays.
- Computes case summary client-side.

### Issue

The summary logic expects nested data:

```text
analisis.muestras_saliva[].resultados[]
```

But the backend serializer only includes `muestras_saliva` and does not include nested `resultados` inside each sample. This should be aligned.

## Component: MainContent.vue

Purpose: displays selected analysis/case content.

### Backend calls

```http
GET /api/analisis/
```

### Inputs

```text
patientId
caseId
```

### Current behavior

- Finds the analysis matching selected patient and case.
- Uses `muestras_saliva` as image list.
- Uses first image as selected image.
- Displays counts if a result is present.

### Limitations

- No call to segmentation microservices.
- No endpoint for segmentation result retrieval.
- No visible persistence of edited polygons.
- Export buttons are UI-only at this stage.

## View: RegistroView.vue

Purpose: register patients, create cases, upload images.

### Backend calls

```http
GET  /api/pacientes/
GET  /api/pacientes/{id}/casos/
GET  /api/casos/{id}/analisis/
POST /api/pacientes/
POST /api/casos/
POST /api/analisis/
POST /api/muestras/
```

### Current workflows

#### Create Patient

Sends:

```json
{
  "nombre": "...",
  "apellido": "...",
  "identificacion": "...",
  "fecha_nacimiento": "YYYY-MM-DD",
  "email": "...",
  "telefono": "..."
}
```

#### Create Case

Sends:

```json
{
  "paciente": 1,
  "titulo": "...",
  "descripcion": "..."
}
```

Optional automatic analysis creation:

```json
{
  "id_paciente_fk": 1,
  "id_caso_fk": 1,
  "estado": 0
}
```

#### Upload Images

For each file:

```text
POST /api/muestras/
Content-Type: multipart/form-data

imagen=<file>
analisis=<analysis_id>
```

## Frontend Configuration Issues

The API base URL is repeated and hardcoded:

```text
http://127.0.0.1:8000
```

Recommended replacement:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Then centralize Axios in:

```text
src/services/apiClient.js
```

## Recommended Frontend Refactor

Target structure:

```text
src/
├── app/
│   └── App.vue
├── components/
│   └── shared/
├── modules/
│   ├── patients/
│   ├── cases/
│   ├── samples/
│   ├── segmentation/
│   ├── characterization/
│   └── reports/
├── services/
│   ├── apiClient.js
│   ├── patientsApi.js
│   ├── casesApi.js
│   ├── analysesApi.js
│   └── samplesApi.js
└── router/
```

## Recommended State Strategy

For a small version:

- Keep component-local state.
- Centralize API calls.

For a more maintainable version:

- Introduce Pinia for patient/case/analysis state.
- Add Vue Router.
- Isolate segmentation editor state.

## Required Frontend Work for Full SICAM

- Add sample type selector: `SALIVA | SANGRE`.
- Add segmentation trigger action.
- Add segmentation job status UI.
- Add polygon/mask editor persistence.
- Add characterization module.
- Add report export module.
- Add authentication/session handling.
