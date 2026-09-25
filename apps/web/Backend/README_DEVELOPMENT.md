# SICAM Backend — Desarrollo local

Django REST orquesta segmentación, persistencia, revisiones y Characterization.
Ambiente **sicam**, Python **3.10.20**, Django **5.0.1**, puerto **8000**.
Characterization se ejecuta aquí, sin otro servicio.

## Instalación y configuración

Para una WSL nueva, seguir la [guía canónica de instalación](../../../docs/developer_environment_setup_wsl.md).
Con el ambiente `sicam` ya creado:

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python -m pip install -r requirements.txt
python -m pip check
[ -f .env ] || cp .env.example .env
python manage.py migrate
python manage.py showmigrations
python manage.py check
```

Revisar `.env` sin sobrescribirlo. SQLite es el default (`db.sqlite3` local);
PostgreSQL es opcional con `DB_*` y su driver ya está declarado. No crear ni
revertir migraciones como paso de instalación. Aplicar todas las versionadas,
incluida `0007_saliva_segmentation_strategy`. Superusuario opcional:
`python manage.py createsuperuser`.

Las variables reales están en [.env.example](.env.example). Routing local:

| Servicio | URL / timeout del ejemplo |
|---|---|
| CURRENT | `SALIVA_SEGMENTATION_SERVICE_URL=http://127.0.0.1:8001`, `SALIVA_SERVICE_TIMEOUT=30` |
| ALT | `SALIVA_ALT_SEGMENTATION_SERVICE_URL=http://127.0.0.1:8003`, `SALIVA_ALT_SERVICE_TIMEOUT=240` |
| BLOOD | `BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002`, `BLOOD_SERVICE_TIMEOUT=240` |

CORS del ejemplo admite localhost y 127.0.0.1 en 5173/3000. Frontend apunta a
Django con `VITE_API_BASE_URL=http://127.0.0.1:8000`. Reiniciar los procesos al
cambiar sus archivos `.env`; mantener secretos fuera de Git.

## Arranque y disponibilidad

```bash
cd ~/repos/sicam-refactor/apps/web/Backend
conda activate sicam
python manage.py runserver 127.0.0.1:8000
```

Desde otra terminal:

```bash
curl --fail http://127.0.0.1:8000/api/
curl --fail http://127.0.0.1:8000/api/pacientes/
```

No hay una ruta `/api/health/` registrada. `/admin/` está disponible para el
superusuario. En desarrollo `DEBUG=True` permite servir imágenes desde `/media/`.
Para levantar los microservicios y frontend, usar el
[manual cotidiano](../../../docs/30_developer_startup_and_test_data.md).

## Contratos y pruebas

SALIVA: `POST /api/muestras/{id}/segmentar/`, JSON con
`segmentation_strategy=CURRENT_CUSTOM_V1` o `ALT_CPSAM_MORPHOLOGICAL_V1`;
si se omite, usa CURRENT. BLOOD: `POST /api/muestras-sangre/{id}/segmentar/`,
sin campo de estrategia. Historial: `resultados-segmentacion/` bajo cada muestra.
El efectivo se consulta en `/api/resultados-segmentacion/{id}/efectivo/`.
VALIDADA > AUTOMATICO; BORRADOR nunca es efectivo.

El seed oficial está documentado en el manual cotidiano. No necesita fixtures
externas y su PNG 1×1 sirve sólo para galería.

```bash
python manage.py check
python -m pytest -q
python manage.py test
```

Los tests están en `api/tests.py`, `api/test_saliva_strategies.py` y
`api/services/segmentation/tests.py`. No existe `api/tests/test_models.py`.
Los tests normales simulan HTTP; no necesitan levantar Cellpose.
Ver también [clientes de segmentación](api/services/segmentation/USAGE.md).
No versionar `.env`, `db.sqlite3`, `media/` ni logs.
