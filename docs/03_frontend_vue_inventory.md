# 03 - Vue Frontend Inventory

## Project

```text
apps/web/Frontend
```

This frontend comes from the previous `micronucleos-web/Frontend` project.

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
src/services/apiClient.js
.env.example
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

## Technical Validation Status

The frontend source now uses the centralized `apiClient`, but a full build validation is still pending in the current environment.

Recommended validation:

```bash
cd apps/web/Frontend
npm install
npm run build
```

During the sanitation pass, `node_modules` was not present, so the build could not be completed without installing dependencies.

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

- `segmentacion`: active UI shell.
- `registro`: implemented.
- `analisis`: placeholder.
- `caracterizacion`: placeholder.

## API Client Configuration

The frontend now centralizes Axios in:

```text
src/services/apiClient.js
```

Current client:

```js
import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

export default apiClient;
```

Environment example:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

No hardcoded `http://127.0.0.1:8000` references remain in `apps/web/Frontend/src`.

## Component: TopBar.vue

Purpose: main navigation between sections.

Observed behavior:

- Emits `change-section`.
- Parent `App.vue` switches active section.

## Component: SideBar.vue

Purpose: search/select patients and cases.

### Backend calls

Through `apiClient`:

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

But the backend serializer currently nests `muestras_saliva` without nested `resultados`. This should be aligned later.

## Component: MainContent.vue

Purpose: displays selected analysis/case content.

### Backend calls

Through `apiClient`:

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

- No frontend action calls a Django segmentation endpoint yet.
- No segmentation result retrieval endpoint exists yet.
- No visible persistence of edited polygons.
- Export buttons are UI-only at this stage.

## View: RegistroView.vue

Purpose: register patients, create cases, upload images.

### Backend calls

Through `apiClient`:

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

Current limitation: uploaded images still map to `MuestraSaliva`; there is no sample type selector for saliva versus blood.

## Configuration Status

Resolved:

- Frontend API URL is externalized through `VITE_API_BASE_URL`.
- Axios is centralized in `src/services/apiClient.js`.
- `.env.example` exists.

Still pending:

- Install dependencies and run a successful frontend build.
- Add a frontend control for sample type (`SALIVA` / `SANGRE`).
- Add a UI action to trigger `POST /api/muestras/{id}/segmentar/` once backend supports it.
- Add segmentation job/status/result UI.
- Document frontend runtime/deployment configuration.

## Recommended Frontend Refactor

Do not introduce Vue Router, Pinia, or a full module rewrite yet.

Low-risk next steps:

1. Keep component-local state.
2. Add small API wrappers around `apiClient` only when duplication grows.
3. Add sample type UI after the backend model/API can represent it.
4. Add segmentation trigger UI after Django exposes the endpoint.

## Required Frontend Work for Full SICAM

- Add sample type selector: `SALIVA | SANGRE`.
- Add segmentation trigger action.
- Add segmentation status/result UI.
- Add polygon/mask editor persistence.
- Add validation workflow UI.
- Add characterization module.
- Add report export module.
- Add authentication/session handling.
