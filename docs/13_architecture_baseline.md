# SICAM - Baseline arquitectonica

## 1. Proposito del documento

Este documento establece la baseline arquitectonica del repositorio `sicam-refactor` despues del saneamiento inicial, la validacion tecnica minima, la remediacion de configuracion y la conversion de `apps/` a carpetas normales dentro del monorepo.

Su objetivo es servir como fuente de verdad para las siguientes iteraciones. No define funcionalidades nuevas ni reemplaza la documentacion historica existente; resume el estado real actual del repositorio y fija restricciones para continuar el refactor sin alterar la logica funcional de forma accidental.

## 2. Estado actual del monorepo

El repositorio funciona ahora como un monorepo autocontenido a nivel de codigo fuente. Las rutas principales bajo `apps/` ya no deben depender de gitlinks ni submodulos:

- `apps/web`
- `apps/segmentation-saliva`
- `apps/segmentation-blood`

La conversion dejo los proyectos como carpetas normales versionables dentro del repositorio raiz. La verificacion esperada es:

- `git ls-files -s apps | Select-String 160000` sin salida.
- `git submodule status` sin salida.

Los artefactos generados o locales deben permanecer fuera del control de versiones, incluyendo `node_modules/`, `dist/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `media/` y modelos o pesos pesados.

## 3. Repos fuente integrados

Este repositorio refactorizado se construyo a partir de tres repositorios fuente previos:

- `micronucleos-web`
- `Segmentacion_web`
- `segmentacion_sangre`

La integracion actual no implica todavia una fusion funcional completa. El objetivo de esta etapa fue preservar el codigo fuente relevante, estabilizar configuracion y dejar una base tecnica inspeccionable antes de implementar el flujo integrado completo.

## 4. Arquitectura actual

El estado actual contiene cuatro areas principales:

- Un backend Django en `apps/web/Backend`.
- Un frontend Vue/Vite en `apps/web/Frontend`.
- Un microservicio FastAPI para segmentacion de saliva en `apps/segmentation-saliva`.
- Un microservicio FastAPI para segmentacion de sangre en `apps/segmentation-blood`.

El backend ya contiene clientes Django para comunicarse con servicios de segmentacion bajo `apps/web/Backend/api/services/segmentation/`. Sin embargo, el flujo completo todavia no esta cerrado porque falta el endpoint Django que dispare segmentacion desde una muestra, la persistencia JSON del resultado y la integracion frontend minima de extremo a extremo.

## 5. Arquitectura objetivo

La arquitectura objetivo sigue siendo:

```text
Frontend Vue -> Django REST -> microservicios FastAPI -> persistencia en Django
```

El frontend debe consumir Django REST mediante un cliente API centralizado. Django debe mantener la propiedad del dominio, autenticacion futura, persistencia y orquestacion del flujo. Los microservicios FastAPI deben encargarse de ejecutar la logica de segmentacion correspondiente sin absorber responsabilidades del dominio principal.

## 6. Componentes existentes

### `apps/web/Backend`

Backend Django principal. Contiene modelos, serializers, vistas, rutas existentes y clientes para microservicios de segmentacion. Actualmente el dominio sigue centrado principalmente en `MuestraSaliva`.

Estado relevante:

- Configuracion externalizada mediante `.env.example`.
- Dependencias declaradas en `requirements.txt`.
- Configuracion de pruebas con `pytest.ini`.
- Clientes de segmentacion en `api/services/segmentation/`.

### `apps/web/Frontend`

Frontend Vue/Vite. Contiene la interfaz actual y usa un cliente API centralizado.

Estado relevante:

- `src/services/apiClient.js` centraliza la base URL.
- La base URL se toma de `import.meta.env.VITE_API_BASE_URL`.
- Existe `apps/web/Frontend/.env.example`.
- `node_modules/` y `dist/` deben permanecer ignorados.

### `apps/segmentation-saliva`

Microservicio FastAPI orientado a segmentacion de saliva. Contiene envolturas API, utilidades y codigo de segmentacion en `segmentacion_core/`.

Estado relevante:

- Tiene `requirements.txt`.
- Contiene codigo fuente liviano de `cellpose/` versionado de forma explicita.
- `segmentacion_core/membranas_500_125` se trata como modelo o artefacto pesado externo y no debe versionarse sin decision explicita.

Nota: la inclusion de `cellpose/` como codigo versionado es una decision temporal para preservar el estado heredado del repositorio fuente. En una iteracion futura debe evaluarse si conviene reemplazarlo por una dependencia externa formal.

### `apps/segmentation-blood`

Microservicio FastAPI orientado a segmentacion de sangre. Contiene envolturas API, utilidades y codigo de segmentacion en `segmentacion_core/`.

Estado relevante:

- Tiene `requirements.txt`.
- Contiene codigo fuente liviano de `cellpose/` versionado de forma explicita.
- No debe arrancarse en validaciones si eso implica cargar modelos pesados.

Nota: la inclusion de `cellpose/` como codigo versionado es una decision temporal para preservar el estado heredado del repositorio fuente. En una iteracion futura debe evaluarse si conviene reemplazarlo por una dependencia externa formal.

## 7. Cerrado hasta ahora

Las siguientes tareas se consideran cerradas para esta baseline:

- Saneamiento inicial del repositorio.
- Eliminacion o exclusion de archivos generados/locales.
- Ajuste de `.gitignore`.
- Externalizacion de configuracion mediante `.env.example`.
- Creacion de `apps/web/Frontend/src/services/apiClient.js`.
- Uso de `VITE_API_BASE_URL` en el frontend.
- Creacion de clientes Django para segmentacion de saliva y sangre.
- Validacion tecnica minima previa con reporte en `docs/11_validation_report.md`. Esta validacion fue anterior a la conversion final a monorepo; todavia se requiere una validacion limpia post-monorepo en el Sprint 1.
- Remediacion tecnica minima documentada en `docs/12_remediation_report.md`.
- Conversion de `apps/web`, `apps/segmentation-saliva` y `apps/segmentation-blood` de gitlinks/submodulos rotos a carpetas normales del monorepo.

## 8. Pendiente

Los pendientes principales antes de considerar el flujo integrado como estable son:

- Ejecutar una validacion tecnica limpia post-monorepo.
- Implementar el endpoint Django `POST /api/muestras/{id}/segmentar/`.
- Persistir resultados JSON de segmentacion en Django.
- Integrar el flujo `frontend -> Django -> microservicio -> persistencia`.
- Generalizar gradualmente `MuestraSaliva` hacia `ImagenMuestra` o un modelo comun para saliva y sangre.
- Agregar validacion, caracterizacion y reportes.
- Documentar despliegue y operacion de cada componente.
- Definir una estrategia explicita para modelos y pesos externos no versionados.

## 9. Riesgos tecnicos actuales

- El modelo de dominio sigue centrado en saliva, especialmente alrededor de `MuestraSaliva`.
- Los modelos, pesos y artefactos pesados no estan versionados y requieren una estrategia externa clara.
- Existe documentacion historica dispersa que puede contener afirmaciones obsoletas.
- No hay pruebas API suficientes del flujo integrado completo.
- Puede haber confusion entre artefactos locales y archivos versionados si no se revisa `git status --ignored --short apps` antes de cerrar iteraciones.
- Los microservicios contienen codigo de segmentacion sensible; cambios pequenos pueden alterar resultados funcionales.

## 10. Reglas para futuras tareas con Codex

Para preservar la estabilidad del refactor, las siguientes reglas aplican salvo instruccion explicita en una iteracion futura:

- No modificar modelos Django salvo sprint explicito.
- No cambiar endpoints existentes sin una estrategia de compatibilidad.
- No tocar codigo de `cellpose/` ni algoritmos de segmentacion sin autorizacion explicita.
- No incluir `node_modules/`, `dist/`, caches, `media/`, bases de datos locales ni modelos/pesos pesados.
- No fusionar los microservicios en Django todavia.
- No reestructurar carpetas sin una tarea dedicada.
- No inferir funcionalidades faltantes desde cero.
- Preferir cambios de dependencia, configuracion y pruebas antes que cambios de logica.
- Mantener `membranas_500_125` y artefactos similares como dependencias externas documentadas, no como archivos versionados por defecto.

## 11. Criterio de estabilidad de la baseline

La baseline se considera estable si se cumplen estas condiciones:

- No existen entradas gitlink `160000`.
- `git submodule status` no reporta submodulos.
- Los artefactos generados permanecen fuera de Git.
- Backend y frontend pasan validaciones minimas.
- Los microservicios pueden inspeccionarse o importarse sin cargar modelos pesados.

Politica de modelos externos: los modelos, pesos y artefactos pesados deben manejarse mediante una estrategia externa, como almacenamiento institucional, release assets, carpeta local documentada o mecanismo de descarga controlado. No deben agregarse al repositorio sin decision explicita.

## 12. Roadmap por sprints

### Sprint 0: baseline arquitectonica

Crear y mantener este documento como fuente de verdad del estado actual del repo.

### Sprint 1: validacion tecnica limpia

Reejecutar validaciones despues de la conversion a monorepo: Django, pytest, frontend build e imports livianos de microservicios sin cargar modelos pesados.

### Sprint 2: endpoint Django de segmentacion

Agregar `POST /api/muestras/{id}/segmentar/` como punto de orquestacion desde Django hacia los clientes de segmentacion existentes.

### Sprint 3: persistencia JSON

Persistir resultados de segmentacion como JSON en Django, sin redisenar de golpe el dominio.

### Sprint 4: integracion frontend minima

Conectar el frontend al flujo Django de segmentacion usando el cliente API centralizado y sin redisenar la UI.

### Sprint 5: generalizacion del dominio

Generalizar gradualmente `MuestraSaliva` hacia `ImagenMuestra` o una abstraccion comun para saliva y sangre, con migraciones y compatibilidad controladas.

### Sprint 6: validacion, caracterizacion y reportes

Agregar validaciones, caracterizacion de resultados, reportes y pruebas del flujo integrado.
