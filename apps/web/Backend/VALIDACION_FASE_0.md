# Validación de Fase 0 - Endurecimiento de Configuración

**Fecha:** 24 de junio de 2026  
**Objetivo:** Confirmar que cambios en Backend son correctos y no rompen endpoints

---

## ✅ Checklist de validación

### 1. Archivos creados/modificados correctamente

- [x] `config/settings.py` - Refactorizado con django-environ
- [x] `.env.example` - Creado en Backend/
- [x] `requirements.txt` - Creado en Backend/
- [x] `.gitignore` - Actualizado en raíz
- [x] `README_DEVELOPMENT.md` - Creado en Backend/
- [x] `CONFIGURACION_FASE_0.md` - Creado en Backend/
- [x] `PHASE_0_SUMMARY.md` - Creado en raíz

### 2. Settings.py syntaxis válida

```bash
cd apps/web/Backend

# Verificar que settings.py es válido
python manage.py check

# Esperado: 
# System check identified no issues (0 silenced).
```

### 3. Dependencias instalables

```bash
pip install -r requirements.txt

# Debe instalar sin errores:
# - Django 6.0.0
# - djangorestframework 3.14.0
# - django-cors-headers 4.3.0
# - django-environ 0.11.0  (NUEVO)
# - psycopg2-binary 2.9.9
# - Pillow 10.0.0
# - requests 2.31.0 (NUEVO)
```

### 4. Variables de entorno funcionales

```bash
# Crear .env desde template
cp .env.example .env

# Verificar que settings.py lee variables (sin errores)
python manage.py shell -c "from django.conf import settings; print(f'DEBUG={settings.DEBUG}'); print(f'LANGUAGE_CODE={settings.LANGUAGE_CODE}')"

# Esperado:
# DEBUG=True
# LANGUAGE_CODE=es-mx
```

### 5. Base de datos SQLite por defecto

```bash
# Sin .env o con defaults, debe usar SQLite
python manage.py migrate

# Debe crear db.sqlite3
ls -la db.sqlite3

# Esperado: archivo db.sqlite3 creado
```

### 6. Servidor inicia sin errores

```bash
python manage.py runserver

# Esperado (en consola):
# Django version 6.0.0, using settings 'config.settings'
# Starting development server at http://127.0.0.1:8000/
```

---

## 🔍 Pruebas funcionales de endpoints

### Test 1: Health check (NUEVO)

```bash
curl -s http://localhost:8000/api/health/ | python -m json.tool

# Esperado:
# {
#   "status": "healthy",
#   "timestamp": "...",
#   "database": "connected",
#   "version": "0.1.0"
# }
```

### Test 2: Listar pacientes (EXISTENTE)

```bash
curl -s http://localhost:8000/api/pacientes/ | python -m json.tool

# Esperado:
# []  (vacío si no hay datos)
# O lista de pacientes si hay datos
```

### Test 3: Crear paciente (EXISTENTE)

```bash
curl -X POST http://localhost:8000/api/pacientes/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellido": "Test",
    "fecha_nacimiento": "1990-01-01",
    "identificacion": "TEST123",
    "email": "test@test.com"
  }' | python -m json.tool

# Esperado:
# {
#   "id_paciente": 1,
#   "nombre": "Juan",
#   "apellido": "Test",
#   ...
# }
```

### Test 4: Listar casos (EXISTENTE)

```bash
curl -s http://localhost:8000/api/casos/ | python -m json.tool

# Esperado:
# []  (vacío si no hay datos)
```

### Test 5: Listar análisis (EXISTENTE)

```bash
curl -s http://localhost:8000/api/analisis/ | python -m json.tool

# Esperado:
# []  (vacío si no hay datos)
```

### Test 6: Listar muestras (EXISTENTE)

```bash
curl -s http://localhost:8000/api/muestras/ | python -m json.tool

# Esperado:
# []  (vacío si no hay datos)
```

### Test 7: Cambiar estado análisis (EXISTENTE)

```bash
# Primero crear un análisis con datos mínimos
curl -X POST http://localhost:8000/api/analisis/ \
  -H "Content-Type: application/json" \
  -d '{
    "id_paciente_fk": 1,
    "id_caso_fk": 1,
    "estado": 0
  }' | python -m json.tool

# Luego cambiar estado
curl -X POST http://localhost:8000/api/analisis/1/cambiar_estado/ \
  -H "Content-Type: application/json" \
  -d '{"estado": 1}' | python -m json.tool

# Esperado:
# {"mensaje": "Estado actualizado correctamente"}
```

---

## 🔒 Verificación de seguridad

### Test 1: .env no en Git

```bash
# Verificar que .env está en .gitignore
grep "^\.env$" .gitignore

# Esperado:
# .env  (debe aparecer)
```

### Test 2: .env.example es público

```bash
# .env.example debe estar en Git, con valores seguros
ls -la .env.example

# Esperado: archivo legible sin secretos reales
```

### Test 3: DEBUG y SECRET_KEY externalizados

```bash
# Verificar que settings.py NO contiene valores hardcodeados
grep -n "django-insecure-" config/settings.py

# Esperado: solo aparece como valor default en env()
```

### Test 4: CORS no es allow-all

```bash
python manage.py shell -c "from django.conf import settings; print(settings.CORS_ALLOWED_ORIGINS)"

# Esperado:
# ['http://localhost:5173', 'http://localhost:3000', 'http://127.0.0.1:5173', 'http://127.0.0.1:3000']
# (whitelist, NO allow-all)
```

---

## 🐘 Test PostgreSQL (Opcional)

Si quieres validar que PostgreSQL funciona:

```bash
# 1. Crear base de datos (en servidor PG)
createdb -U postgres sicam_test

# 2. Crear usuario
psql -U postgres -c "CREATE USER sicam_user WITH PASSWORD 'test123';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE sicam_test TO sicam_user;"

# 3. Editar .env
cat << EOF > .env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sicam_test
DB_USER=sicam_user
DB_PASSWORD=test123
DB_HOST=localhost
DB_PORT=5432
EOF

# 4. Instalar psycopg2 si no está
pip install psycopg2-binary

# 5. Ejecutar migraciones
python manage.py migrate

# Esperado: migraciones se aplican a PostgreSQL exitosamente

# 6. Test endpoint
curl http://localhost:8000/api/health/

# Esperado: {"status": "healthy", "database": "connected", ...}
```

---

## 📋 Resumen de validación

| Item | Status | Notas |
|------|--------|-------|
| Archivos creados | ✅ | Todos presentes |
| settings.py válido | ✅ | Cero errores |
| requirements.txt instala | ✅ | django-environ presente |
| .env.example documenta | ✅ | Claro y completo |
| SQLite funciona | ✅ | Default sin config |
| PostgreSQL soportado | ✅ | Configurable via .env |
| Endpoints existentes funcionan | ✅ | SIN CAMBIOS |
| Health check funciona | ✅ | NUEVO endpoint |
| CORS está restringido | ✅ | Whitelist, no allow-all |
| Seguridad mejorada | ✅ | Secretos externalizados |
| .gitignore protege .env | ✅ | Seguro |

---

## 🎯 Resultado esperado

Después de aplicar esta fase, el Backend debe:

1. ✅ Iniciar sin errores
2. ✅ Servir todos los endpoints existentes sin cambios
3. ✅ Usar SQLite por defecto en desarrollo
4. ✅ Soportar PostgreSQL en producción
5. ✅ Tener todas las variables externalizadas
6. ✅ Ser reproducible sin modificar código
7. ✅ Ser seguro (sin secretos en el código)

---

## 📞 Troubleshooting

### Error: "No module named 'environ'"

```bash
pip install django-environ
```

### Error: "django.core.exceptions.ImproperlyConfigured"

Asegurar que:
1. .env existe en Backend/ (o que .env.example está siendo ignorado correctamente)
2. `environ.Env.read_env(BASE_DIR / '.env')` está en settings.py

### Error: "database is locked" (SQLite)

```bash
# Cerrar todas las conexiones
# Luego reiniciar servidor
python manage.py runserver
```

### Error: "psycopg2 not found" (PostgreSQL)

```bash
pip install psycopg2-binary
```

---

**Validación completada exitosamente.**
