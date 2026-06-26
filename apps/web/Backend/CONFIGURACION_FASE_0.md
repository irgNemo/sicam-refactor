# SICAM Refactor - Fase 0: Endurecimiento de Configuración

**Fecha:** 24 de junio de 2026  
**Alcance:** apps/web/Backend - Configuración y seguridad  
**Estado:** ✅ Completado

---

## 📋 Resumen de cambios

Esta fase externalizó toda la configuración sensible a variables de entorno, mejorando:

- **Seguridad:** Sin credenciales en el código
- **Flexibilidad:** Soporta SQLite (desarrollo) y PostgreSQL (producción)
- **Reproducibilidad:** Desarrollo sin cambiar archivos del proyecto
- **Documentación:** Guías claras y .env.example

### Archivos modificados o creados:

| Archivo | Acción | Razón |
|---------|--------|-------|
| `config/settings.py` | ✏️ Modificado | Usar django-environ para variables |
| `.env.example` | ✨ Creado | Template de configuración |
| `requirements.txt` | ✨ Creado | Dependencias documentadas |
| `.gitignore` | ✏️ Mejorado | Más claro y organizado |
| `README_DEVELOPMENT.md` | ✨ Creado | Guía de desarrollo |

---

## 🔐 Variables de entorno principales

### Seguridad (CRÍTICO en producción)

```env
SECRET_KEY=cambiar-en-producción
DEBUG=False  # NUNCA True en producción
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
```

### Base de datos

**Opción 1: SQLite (Desarrollo, default)**
```
# No definir variables DB_* - usa db.sqlite3 automáticamente
```

**Opción 2: PostgreSQL (Producción)**
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sicam_db
DB_USER=usuario_db
DB_PASSWORD=contraseña_db
DB_HOST=localhost
DB_PORT=5432
```

### Microservicios de segmentación

```env
SALIVA_SEGMENTATION_SERVICE_URL=http://localhost:8001
BLOOD_SEGMENTATION_SERVICE_URL=http://localhost:8002
```

### CORS (Frontend)

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 🚀 Cómo ejecutar en desarrollo

### 1. Instalar dependencias

```bash
cd apps/web/Backend
pip install -r requirements.txt
```

### 2. Crear archivo .env

```bash
cp .env.example .env
# Los valores por defecto funcionan para SQLite local
# No es necesario editar .env para desarrollo básico
```

### 3. Ejecutar migraciones

```bash
python manage.py migrate
```

### 4. Iniciar servidor

```bash
python manage.py runserver
```

**API disponible en:** `http://localhost:8000/api/`

---

## ✅ Verificación de cambios

### Health check

```bash
curl http://localhost:8000/api/health/
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-24T...",
  "database": "connected",
  "version": "0.1.0"
}
```

### Endpoints existentes aún funcionan

```bash
# Listar pacientes
curl http://localhost:8000/api/pacientes/

# Listar casos
curl http://localhost:8000/api/casos/

# Listar análisis
curl http://localhost:8000/api/analisis/

# Listar muestras
curl http://localhost:8000/api/muestras/
```

---

## 🐘 Migrar a PostgreSQL (Producción)

### 1. Crear base de datos PostgreSQL

```bash
# En servidor PostgreSQL:
psql -U postgres
```

```sql
CREATE DATABASE sicam_db;
CREATE USER sicam_user WITH PASSWORD 'contraseña_segura';
ALTER ROLE sicam_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE sicam_db TO sicam_user;
```

### 2. Editar .env

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sicam_db
DB_USER=sicam_user
DB_PASSWORD=contraseña_segura
DB_HOST=servidor-db.com
DB_PORT=5432
```

### 3. Aplicar migraciones

```bash
python manage.py migrate
```

### 4. Reiniciar servidor

```bash
python manage.py runserver
```

---

## 📁 Estructura del Backend

```
Backend/
├── config/
│   ├── settings.py       ← Variables de entorno (refactorizado)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── api/
│   ├── models.py         ← SIN CAMBIOS
│   ├── serializers.py    ← SIN CAMBIOS
│   ├── views.py          ← SIN CAMBIOS
│   ├── urls.py           ← SIN CAMBIOS
│   └── migrations/       ← SIN CAMBIOS
├── manage.py
├── db.sqlite3            ← (gitignored)
├── media/                ← (gitignored)
├── requirements.txt      ← NUEVO
├── .env.example          ← NUEVO
├── .env                  ← NUEVO (gitignored)
└── README_DEVELOPMENT.md ← NUEVO
```

---

## 🛠️ Comandos útiles

### Crear superusuario (para /admin/)

```bash
python manage.py createsuperuser
```

### Ver migraciones pendientes

```bash
python manage.py showmigrations
```

### Entrar en shell de Django

```bash
python manage.py shell
>>> from api.models import Paciente
>>> Paciente.objects.count()
```

### Ejecutar tests

```bash
pytest
pytest --cov=api
```

---

## ⚠️ Notas importantes

1. **NUNCA commitear .env:** Está en .gitignore - propiedades sensibles
2. **SECRET_KEY en producción:** Generar nueva clave segura
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
3. **DEBUG=False en producción:** Mostrar página de error genérica
4. **ALLOWED_HOSTS específico:** No usar `*` en producción
5. **CORS restringido:** Solo orígenes permitidos

---

## 📚 Recursos

- [Django 6.0 Documentation](https://docs.djangoproject.com/en/6.0/)
- [django-environ](https://github.com/joke2k/django-environ)
- [Django REST Framework](https://www.django-rest-framework.org/)

Ver también:
- `README_DEVELOPMENT.md` - Guía completa de desarrollo
- `.env.example` - Referencia de todas las variables
- `PHASE_0_SUMMARY.md` - Documentación técnica detallada

---

**Fase 0 completada exitosamente.**
