# Despliegue de producción de SICAM

Actualizado: 2026-10-26. Contrato preparado en Sprint 18T-C; **no describe un
servidor productivo ya configurado**. No use Vite dev server ni Django runserver
como servidores de producción.

## Condiciones previas

1. Elegir servidor, dominio real, certificados HTTPS, almacenamiento, usuario de
   servicio y servidor WSGI. No hay una instalación de Nginx/Gunicorn gestionada
   por este sprint.
2. Resolver `DJANGO_SUPPORTED_RELEASE_UPGRADE`: el pin y el entorno auditado usan
   **Django 5.0.1**. Django 5.0 ya no recibe soporte; configurar headers no corrige
   vulnerabilidades de dependencias. Planificar actualización a una rama
   soportada, revisar también el resto de dependencias y repetir regresiones.
   No se cambiaron requirements ni se instalaron paquetes en 18T-C.
3. Validar el despliegue en staging y disponer de un backup restaurable antes de
   exponer acceso real. No se debe publicar una BD con datos clínicos para probar
   la configuración.
4. Revisar las cuentas operativas de prueba: OPERATOR ID 3 y REVIEWER ID 4 están
   documentadas como cuentas de aceptación en 18T-A.1. El nombre actual no tiene
   un prefijo TEST inequívoco; la aplicación no les asigna esa condición ni las
   desactiva automáticamente. Revisar también las cuentas ADMIN/plataforma.

La documentación oficial advierte del fin de soporte de la rama instalada:
[Django 5.0 deployment checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/).
Consultar [versiones soportadas](https://www.djangoproject.com/download/) al elegir
la actualización, sin asumir que el pin de este documento seguirá siendo actual.

## Entorno y dependencias

Backend: `apps/web/Backend`; aplicación WSGI: `config.wsgi:application`.
Frontend: `apps/web/Frontend`; Node usado para validar: **24.17.0**.
Microservicios científicos se despliegan separadamente con sus entornos actuales;
no se cambian por este contrato.

En un entorno aislado de staging/producción, después de resolver la actualización
y aprobar los pins correspondientes:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

No ejecutar instalaciones sobre los entornos científicos de trabajo. El entorno
`sicam` actual no contiene Gunicorn y requirements no lo declara. Se mantiene
`WSGI_PRODUCTION_SERVER = DEPLOYMENT_DECISION`. Elegir/versionar el servidor WSGI
con una validación propia; el proxy debe apuntar a su socket o puerto privado.
No se prescribe un comando Gunicorn que dependa de un paquete no instalado.

SQLite continúa siendo el motor actual. No se migró a PostgreSQL.
`SQLITE_PRODUCTION_SCALABILITY = FUTURE_DEPLOYMENT_DECISION`: evaluar concurrencia,
operaciones científicas largas y volumen con el uso esperado; no asumir que SQLite
es automáticamente inválido ni que tolerará cualquier carga.

## Variables y secretos

Usar `apps/web/Backend/.env.production.example` como **plantilla de variables del
proceso**, no como un archivo con credenciales listo para publicar. Completar un
archivo privado fuera del checkout o un gestor de secretos. El gestor del servicio
puede cargarlo con su mecanismo de environment protegido; no colocarlo dentro del
webroot ni copiarlo a artefactos frontend.

- `DJANGO_ENV=production`: no carga automáticamente el `.env` de desarrollo.
- `DJANGO_SECRET_KEY`: obligatorio, aleatorio, único, al menos 50 caracteres; no
  se acepta el prefijo `django-insecure-`. Generarlo fuera de logs/chat/CI público.
- `DJANGO_DEBUG=False`: un True en producción detiene el arranque.
- `DJANGO_ALLOWED_HOSTS`: hosts reales explícitos, separados por comas, sin
  esquema, wildcard ni subdominios implícitos. Se rechaza una lista vacía.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: orígenes HTTPS explícitos. Puede estar vacío si
  frontend y backend comparten origen, con Host y scheme correctamente reenviados.
- `DJANGO_CORS_ALLOWED_ORIGINS`: vacío para mismo origen. Si existe separación
  aprobada, especificar cada origen HTTPS; no usar `CORS_ALLOW_ALL_ORIGINS`.
- `DJANGO_MEDIA_ROOT`: directorio privado, separado de static y del dist frontend.
- `DJANGO_STATIC_ROOT`: destino de `collectstatic`, públicamente servible.
- `DB_NAME`: ruta absoluta de SQLite o configuración de BD elegida; no apuntar
  accidentalmente a la BD de desarrollo.
- URLs/timeouts de los microservicios: mantener configuración privada y accesible
  sólo desde los componentes autorizados.

En desarrollo, `DJANGO_ENV=development` sigue siendo el valor por defecto y se
conservan las variables legacy SECRET_KEY/DEBUG/ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS.
Los nombres `DJANGO_*` tienen precedencia. Si la shell define un `DEBUG` ajeno a
Django, configurar `DJANGO_DEBUG=True` explícitamente para desarrollo HTTP.
No se modificó el `.env` real durante el sprint. Ambos `.env` reales están ignorados
por Git; las plantillas no contienen secretos reales.

## Cookies, sesiones y HTTPS

Producción exige:

- SESSION_COOKIE_SECURE y CSRF_COOKIE_SECURE verdaderos.
- Session cookie HttpOnly, SameSite=Lax; CSRF SameSite=Lax y **no HttpOnly**, porque
  Axios puede leer `csrftoken`; el bootstrap además devuelve `csrf_token`.
- SECURE_SSL_REDIRECT=True.
- X_FRAME_OPTIONS=DENY, nosniff y Referrer-Policy=same-origin.
- `DJANGO_SESSION_COOKIE_AGE=28800` por defecto (8 horas), configurable; no se
  renueva en cada request. Desarrollo conserva el valor de dos semanas.
- Los cuatro validators Django de contraseña siguen habilitados.

`DJANGO_TRUST_PROXY=True` sólo después de comprobar que el proxy **sobrescribe**
X-Forwarded-Proto y que nadie puede acceder directamente al upstream. Esa opción
activa `SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')`. No confiar en
un header suministrado por clientes públicos. Sin ella, una terminación TLS en
Nginx puede producir bucles de redirección; resolver la configuración del proxy,
no desactivar las cookies seguras.

HSTS comienza con 60 segundos. Después de validar HTTPS integralmente, aumentar
max-age de forma gradual. INCLUDE_SUBDOMAINS y PRELOAD permanecen False hasta
verificar todos los subdominios y aprobar expresamente esa política; no activar
preload sólo para hacer desaparecer un warning.

Login usa `django.contrib.auth.login`, que rota la sesión; logout la invalida.
Usuarios/instituciones inactivos y cambio obligatorio de contraseña bloquean el
acceso operacional. No hay rate limiter nuevo:
`LOGIN_RATE_LIMITING = DEPLOYMENT/FUTURE_HARDENING`.

## Preparación de aplicación

Con el environment productivo ya cargado, backup verificado y ventana de cambio:

```bash
python manage.py check
python manage.py showmigrations api
python manage.py migrate --plan
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
python manage.py check --deploy
```

`migrate` es un paso de despliegue autorizado, no una acción del endpoint health.
La migración 0013 sólo añade índices de LifecycleEvent; no cambia contenido
científico. No copiar la BD de pruebas de pytest a producción.

Frontend:

```bash
npm ci
VITE_API_BASE_URL= npm run build
```

Esto compila llamadas relativas al mismo origen y evita incluir el backend
`127.0.0.1:8000` del `.env` de desarrollo. Verificar el valor en el build final.
Publicar únicamente `dist/`; no exponer repositorio, `.env`, node_modules, SQLite,
backups ni MEDIA_ROOT. Si se aprueba otro origen, definir VITE_API_BASE_URL con ese
origen y revisar cookies/CORS/CSRF; la configuración actual recomienda mismo origen.

Bootstrap administrativo sólo en una BD nueva:

```bash
python manage.py bootstrap_institution --help
python manage.py create_sicam_admin --help
```

Usar los argumentos/interacción de esos comandos y la institución real aprobada.
No crear nuevamente LASAID ni el administrador existente. No incluir contraseñas
reales en scripts, documentación o argumentos que queden en historial.

## Media privada y static público

**STATIC es público; MEDIA científico es privado.** Se sirven por mecanismos
separados. Los endpoints de media autorizados son:

- `/api/private-media/saliva/<id>/`
- `/api/private-media/sangre/<id>/`
- `/api/private-media/calibration/<id>/`
- `/api/private-media/imagej-mask/<uuid>/`

Django comprueba sesión, estado operacional del usuario e institución del objeto,
incluso si está archivado. Anónimo recibe 403 y otra institución 404. Las rutas
`/media/` no están registradas como públicas en Django.

Dos modos soportados:

1. `DJANGO_PRIVATE_MEDIA_DELIVERY=django` (default): Django devuelve FileResponse
   después de autorizar. Es la alternativa segura si todavía no está validado
   X-Accel. Nginx **no** debe añadir un alias público a MEDIA_ROOT.
2. `DJANGO_PRIVATE_MEDIA_DELIVERY=nginx`: Django comprueba permisos, existencia y
   que el path resuelto esté dentro de MEDIA_ROOT; devuelve X-Accel-Redirect hacia
   `/_sicam_private_media/`. Nginx entrega el archivo mediante una location
   **internal**. Django y Nginx necesitan la misma vista del almacenamiento local.
   Este modo no soporta un storage remoto sin `path`; elegir el modo adecuado.

Cabeceras de media: Cache-Control private/no-store, Vary Cookie y nosniff.
No habilitar proxy_cache sobre media ni endpoints autenticados.

Ejemplo **no ejecutable sin sustituir placeholders**, dentro de una configuración
Nginx revisada para el servidor elegido:

```nginx
# Sustituir PUBLIC_HOST, *_PATH y WSGI_PRIVATE_UPSTREAM por valores aprobados.
server {
    listen 80;
    server_name PUBLIC_HOST;
    return 301 https://PUBLIC_HOST$request_uri;
}
server {
    listen 443 ssl;
    server_name PUBLIC_HOST;
    ssl_certificate TLS_CERTIFICATE_PATH;
    ssl_certificate_key TLS_PRIVATE_KEY_PATH;
    root FRONTEND_DIST_PATH;

    # Fijar límite según los endpoints reales (p.ej. lote de calibración),
    # incluyendo multipart overhead; validar tanto API como proxy.
    client_max_body_size 140m;

    location ^~ /api/ {
        proxy_pass http://WSGI_PRIVATE_UPSTREAM;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache off;
    }
    # Consola de plataforma: misma protección de transporte; restringir
    # adicionalmente por red según el despliegue. No es la UI institucional.
    location ^~ /admin/ {
        proxy_pass http://WSGI_PRIVATE_UPSTREAM;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache off;
    }
    location ^~ /static/ {
        alias BACKEND_STATIC_ROOT_PATH/;
        autoindex off;
    }
    location = /media { return 404; }
    location ^~ /media/ { return 404; }

    # Sólo si PRIVATE_MEDIA_DELIVERY=nginx. Nunca quitar "internal".
    location ^~ /_sicam_private_media/ {
        internal;
        alias PRIVATE_MEDIA_ROOT_PATH/;
        autoindex off;
        disable_symlinks on;
        add_header Cache-Control "private, no-store" always;
        add_header Vary "Cookie" always;
        add_header X-Content-Type-Options "nosniff" always;
    }
    location / {
        try_files $uri $uri/ /index.html;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header Referrer-Policy same-origin always;
        # Aplicar también la política HSTS aprobada a la SPA/static en Nginx;
        # la cabecera Django sólo cubre respuestas que pasan por el backend.
    }
}
```

Configurar además un default server que rechace hosts no reconocidos. Ajustar
permisos de almacenamiento, upstream privado, timeouts del proxy y certificados.
El ejemplo no configura el servidor real, ni certifica esos ajustes. Verificar
herencia de `add_header` en la versión de Nginx elegida. El proxy no debe registrar
bodies/cookies/tokens ni query strings potencialmente sensibles. Restringir y
rotar logs; usar un formato de access log sin `$request`/`$args` si pueden contener
identificadores sensibles. No asumir que el formateador Django protege logs Nginx.

Referencias: [Nginx internal](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal)
y [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## Logging y diagnóstico

`LifecycleEvent` sigue siendo la auditoría persistente. Su API y consola son
read-only. Los intentos 403/409 no crean eventos de acciones inexistentes.

`api.operational_logging` registra outcomes de auth/lifecycle y respuestas de
error, con IDs técnicos, institución, route pattern y status. No registra cuerpos,
contraseñas, cookies, tokens, motivos o resultados científicos completos.
El formateador de producción ignora mensajes libres, argumentos y tracebacks.
Errores API 5xx se convierten a mensajes genéricos conservando status; desarrollo
conserva el detalle habitual. Usar logs de infraestructura con la misma disciplina.
El detalle forense técnico queda limitado deliberadamente: este sprint no es APM.

Administración → Diagnóstico permite comprobar BD, migraciones, ownership,
autores, relaciones y coherencia de adquisición. «Verificar archivos» comprueba
existencia de referencias mediante storage.exists, sin hashes ni reparaciones.
Sólo ADMIN/SUPERUSER acceden; los IDs son de su institución o del ámbito global
permitido. NULL ownership sólo puede inspeccionarlo plataforma. No se ofrece un
health público con datos sensibles.

La UI sigue indicando `PRODUCTION_MEDIA_ACCESS_CONTROL = DEPLOYMENT_ACTION_REQUIRED`:
la aplicación no puede probar que un Nginx externo no tenga un alias público.
No hay barrido/borrado automático de archivos huérfanos.

## Backup y recuperación

Procedimiento para producción (los backups de `/tmp` de sprints son temporales,
no una estrategia durable de retención):

1. Definir ubicación privada durable fuera de repo/webroot y una política de
   retención. Restringir permisos; cifrar y proteger acceso según operación.
2. Pausar escrituras coordinadamente para obtener consistencia entre BD y media;
   detener workers/importadores y operaciones de usuarios, sin matar procesos a
   ciegas. Registrar HEAD, migraciones, conteos y hora.
3. Para SQLite, usar `sqlite3.Connection.backup` o `.backup`. No copiar únicamente
   db.sqlite3 durante escrituras/WAL activos. Hash SHA-256 de la copia; abrirla
   read-only y ejecutar integrity_check y foreign_key_check.
4. Copiar MEDIA_ROOT preservando estructura, por ejemplo rsync/cp -a/tar según
   herramientas del despliegue. Guardar manifest por ruta relativa, tamaño y
   SHA-256. **Un manifest no sustituye la copia de los archivos.**
5. Verificar copia BD/media y realizar un ensayo de restauración aislado antes
   de confiar en el procedimiento. No publicar ese entorno de prueba.
6. Restauración: coordinar ventana sin escrituras, preservar el estado actual
   antes de reemplazar, recuperar el par BD+media de la misma generación y
   permisos correctos. Resolver sidecars WAL mediante el procedimiento SQLite
   con conexiones cerradas; no mezclarlos con otro snapshot.
7. Verificar migraciones/conteos, integrity_check, foreign_key_check, referencias
   y hashes. Comprobar media autorizada y rechazo de accesos indebidos antes de
   reabrir operación. No restaurar automáticamente una aceptación exitosa.

No hay scheduler, purga ni retención automática en este sprint.
`ARCHIVED_DATA_RETENTION_POLICY = PENDING_DECISION` y
`ORPHAN_MEDIA_CLEANUP = PENDING_ADMIN_ACTION`.

## Checklist de salida

- [ ] Dependencias soportadas y vulnerabilidades revisadas; regresión completa.
- [ ] Secret real privado, DEBUG=False, hosts exactos, CSRF/CORS revisados.
- [ ] HTTPS y proxy headers confiables; upstream inaccesible públicamente.
- [ ] WSGI elegido y servicio supervisado; no runserver/Vite dev.
- [ ] Build frontend usa el origen aprobado; static separado de media.
- [ ] `/media/...` y location internal directas devuelven 404 en Nginx real.
- [ ] Media: anónimo denegado, otra institución denegada, autorizado recibe archivo;
      comprobar también máscaras ImageJ y referencias de calibración.
- [ ] Sin caché pública de auth/admin/media; headers en SPA/static/backend.
- [ ] Sesión, logout, inactivos y último ADMIN verificados.
- [ ] Auditoría, archivados, restauración y diagnóstico revisados visualmente.
- [ ] `check --deploy` ejecutado en el environment real y avisos documentados.
- [ ] Backups durables/restauración probada y permisos/logging revisados.
- [ ] Cuentas TEST y objetos TEST revisados sin purga improvisada.
- [ ] HSTS gradual, subdominios/preload decididos expresamente.
- [ ] Rate limiting del login y límites/timeouts de upload decididos.

Clasificar por separado: aplicación preparada para revisión; documentación de
despliegue disponible; **seguridad de producción pendiente de actualización de
Django, infraestructura y aceptación real**. Un check automático limpio no prueba
ninguna de las tres por sí solo.
