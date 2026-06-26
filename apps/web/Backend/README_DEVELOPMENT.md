# SICAM Backend - Guía de Desarrollo

## Requisitos previos

- Python 3.10 o superior
- pip (gestor de paquetes Python)
- PostgreSQL 12+ (opcional, para producción)

## Instalación rápida (Desarrollo local con SQLite)

### 1. Crear y activar ambiente virtual

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Crear archivo .env desde el template

```bash
# Copiar .env.example a .env
cp .env.example .env

# Editar .env si necesario (opcional para desarrollo local)
# Los valores por defecto funcionan para SQLite local
```

### 4. Aplicar migraciones de base de datos

```bash
python manage.py migrate
```

### 5. Crear superusuario (opcional, para acceso a /admin/)

```bash
python manage.py createsuperuser
```

### 6. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

La API estará disponible en: `http://localhost:8000/api/`

Panel administrativo: `http://localhost:8000/admin/` (si creaste superusuario)

---

## Verificar que endpoints funcionan

### Health check

```bash
curl http://localhost:8000/api/health/
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-24T10:30:00Z",
  "database": "connected",
  "version": "0.1.0"
}
```

### Listar pacientes

```bash
curl http://localhost:8000/api/pacientes/
```

### Ver documentación de API (si DRF tiene esquema)

```bash
# Browsable API
http://localhost:8000/api/

# Todos los endpoints disponibles
http://localhost:8000/api/pacientes/
http://localhost:8000/api/casos/
http://localhost:8000/api/analisis/
http://localhost:8000/api/muestras/
```

---

## Configuración para PostgreSQL (Producción)

### 1. Instalar PostgreSQL

Consultar docs de PostgreSQL para tu SO.

### 2. Crear base de datos y usuario

```sql
CREATE DATABASE sicam_db;
CREATE USER sicam_user WITH PASSWORD 'cambiar_esta_contraseña';
ALTER ROLE sicam_user SET client_encoding TO 'utf8';
ALTER ROLE sicam_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sicam_user SET default_transaction_deferrable TO on;
ALTER ROLE sicam_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE sicam_db TO sicam_user;
```

### 3. Configurar .env para PostgreSQL

Editar `.env` y descomentar/configurar:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sicam_db
DB_USER=sicam_user
DB_PASSWORD=cambiar_esta_contraseña
DB_HOST=localhost
DB_PORT=5432
```

### 4. Instalar adaptador PostgreSQL

```bash
pip install psycopg2-binary
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

---

## Configurar microservicios de segmentación

### .env - Variables necesarias

Para usar los servicios de segmentación, configurar en `.env`:

```env
# Para segmentación de saliva (default: localhost:8001)
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
SALIVA_SERVICE_TIMEOUT=30

# Para segmentación de sangre (default: localhost:8002)
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
BLOOD_SERVICE_TIMEOUT=30
```

### Verificar que los servicios están en línea

```bash
# Si los servicios están corriendo localmente:
curl http://localhost:8001/health   # Saliva
curl http://localhost:8002/health   # Sangre
```

---

## Configurar CORS (Frontend)

Por defecto, el backend permite requests desde:
- `http://localhost:5173` (Vue dev server)
- `http://localhost:3000` (Alternative port)

Para producción, editar `.env`:

```env
CORS_ALLOWED_ORIGINS=https://frontend.sicam.com,https://www.sicam.com
```

---

## Comandos útiles de Django

### Migraciones

```bash
# Ver migraciones pendientes
python manage.py showmigrations

# Aplicar migraciones
python manage.py migrate

# Crear nueva migración (después de cambiar modelos)
python manage.py makemigrations

# Revertir a una migración anterior
python manage.py migrate api 0001
```

### Base de datos

```bash
# Entrar en shell interactivo de Django
python manage.py shell

# Acceso a REPL con modelos importados
>>> from api.models import Paciente
>>> Paciente.objects.count()
```

### Tests

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=api

# Tests de un módulo específico
pytest api/tests/test_models.py
```

### Tareas administrativas

```bash
# Crear superusuario
python manage.py createsuperuser

# Cambiar contraseña de usuario
python manage.py changepassword username

# Limpiar datos de sesiones expiradas
python manage.py clearsessions
```

---

## Solucionar problemas comunes

### Error: "No module named 'django'"

```bash
# Verificar que ambiente virtual está activado
# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: "django.core.exceptions.ImproperlyConfigured"

- Verificar que `.env` existe en el directorio Backend
- Revisar que variables en `.env` son válidas

### Error: "psycopg2 not found" (si quisiste usar PostgreSQL)

```bash
pip install psycopg2-binary
```

### SQLite database is locked

```bash
# Cerrar todas las conexiones al servidor
# Luego reiniciar:
python manage.py runserver
```

---

## Estructura de carpetas Backend

```
Backend/
├── config/                  # Configuración principal de Django
│   ├── settings.py         # Settings (externalizado a .env)
│   ├── urls.py             # URLs raíz
│   ├── wsgi.py             # Servidor WSGI
│   └── asgi.py             # Servidor ASGI
├── api/                    # Aplicación principal de API
│   ├── models.py           # Modelos Django
│   ├── serializers.py      # Serializadores DRF
│   ├── views.py            # Viewsets de API
│   ├── urls.py             # Router de API
│   ├── migrations/         # Migraciones de BD
│   ├── tests.py            # Tests (vacío)
│   └── admin.py            # Configuración de admin (vacía)
├── manage.py               # Script de administración Django
├── db.sqlite3              # BD local (gitignored)
├── media/                  # Archivos cargados (gitignored)
├── requirements.txt        # Dependencias Python
├── .env.example            # Template de variables de entorno
├── .env                    # Variables de entorno (gitignored)
└── README_DEVELOPMENT.md   # Esta guía
```

---

## Variables de entorno - Referencia completa

Consultar `.env.example` para:
- Descripción completa de cada variable
- Valores por defecto
- Ejemplos de configuración

---

## URLs de API

Todos los endpoints están bajo `/api/`:

```
GET    /api/health/                         # Health check
GET    /api/pacientes/                      # Listar pacientes
POST   /api/pacientes/                      # Crear paciente
GET    /api/pacientes/{id}/                 # Obtener paciente
GET    /api/pacientes/{id}/casos/           # Casos de paciente

GET    /api/casos/                          # Listar casos
POST   /api/casos/                          # Crear caso
GET    /api/casos/{id}/                     # Obtener caso
GET    /api/casos/{id}/analisis/            # Análisis de caso

GET    /api/analisis/                       # Listar análisis
POST   /api/analisis/                       # Crear análisis
GET    /api/analisis/{id}/                  # Obtener análisis
POST   /api/analisis/{id}/cambiar_estado/   # Cambiar estado

GET    /api/muestras/                       # Listar muestras
POST   /api/muestras/                       # Subir muestra (multipart)
GET    /api/muestras/{id}/                  # Obtener muestra
```

---

## Documentación adicional

- [Django 6.0 docs](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [django-environ](https://github.com/joke2k/django-environ)

---

**Última actualización:** 24 de junio de 2026
