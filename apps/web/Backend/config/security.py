"""Environment policy; pure input mapping so production failures can be tested safely."""
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlsplit

DEV_KEY = 'django-insecure-validation-default-key-change-in-production'


def security_settings(values):
    environment = values.get('DJANGO_ENV', 'development').strip().lower()
    if environment not in ('development', 'production'):
        raise ImproperlyConfigured('DJANGO_ENV must be development or production.')
    production = environment == 'production'

    def value(name, default='', legacy=None):
        return values.get('DJANGO_'+name, values.get(legacy or name, default) if not production else default)

    def boolean(name, default, legacy=None):
        raw = str(value(name, default, legacy)).strip().lower()
        if not production and 'DJANGO_'+name not in values and (legacy or name) in values:
            # Preserve django-environ semantics for existing development variables.
            return raw in ('true', '1', 'yes', 'y', 'on')
        if raw not in ('true', 'false', '1', '0'):
            raise ImproperlyConfigured('Invalid boolean: DJANGO_'+name)
        return raw in ('true', '1')

    def number(name, default, minimum=0):
        try:
            n = int(value(name, default))
            if n >= minimum:
                return n
        except (ValueError, TypeError):
            pass
        raise ImproperlyConfigured('Invalid integer: DJANGO_'+name)

    def array(name, default):
        return [v.strip() for v in str(value(name, default)).split(',') if v.strip()]

    secret = value('SECRET_KEY', '' if production else DEV_KEY)
    debug = boolean('DEBUG', not production)
    hosts = array('ALLOWED_HOSTS', '' if production else 'localhost,127.0.0.1,0.0.0.0')
    cors = array('CORS_ALLOWED_ORIGINS', '' if production else 'http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000')
    csrf = array('CSRF_TRUSTED_ORIGINS', '' if production else ','.join(cors))
    all_origins = boolean('CORS_ALLOW_ALL_ORIGINS', False)
    secure_session = boolean('SESSION_COOKIE_SECURE', production or not debug)
    secure_csrf = boolean('CSRF_COOKIE_SECURE', production or not debug)
    redirect = boolean('SECURE_SSL_REDIRECT', production)
    if production:
        if not secret or len(secret) < 50 or len(set(secret)) < 5 or secret.startswith('django-insecure-'):
            raise ImproperlyConfigured('Production requires a unique random DJANGO_SECRET_KEY (at least 50 characters).')
        if debug:
            raise ImproperlyConfigured('DJANGO_DEBUG must be false in production.')
        if not hosts or any('*' in host or '://' in host or '/' in host or host.startswith('.') for host in hosts):
            raise ImproperlyConfigured('Production requires explicit DJANGO_ALLOWED_HOSTS; wildcards are forbidden.')
        if all_origins:
            raise ImproperlyConfigured('Production forbids CORS_ALLOW_ALL_ORIGINS.')
        for origin in cors + csrf:
            parsed = urlsplit(origin)
            if parsed.scheme != 'https' or not parsed.netloc or '*' in origin or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ImproperlyConfigured('Production CORS/CSRF origins must be explicit HTTPS origins.')
        if not secure_session or not secure_csrf or not redirect:
            raise ImproperlyConfigured('Production requires secure cookies and HTTPS redirect.')
    delivery = value('PRIVATE_MEDIA_DELIVERY', 'django')
    if delivery not in ('django', 'nginx'):
        raise ImproperlyConfigured('DJANGO_PRIVATE_MEDIA_DELIVERY must be django or nginx.')
    return dict(DJANGO_ENV=environment, SECRET_KEY=secret, DEBUG=debug, ALLOWED_HOSTS=hosts,
                CORS_ALLOWED_ORIGINS=cors, CORS_ALLOW_ALL_ORIGINS=all_origins,
                CORS_ALLOW_CREDENTIALS=True, CSRF_TRUSTED_ORIGINS=csrf,
                SESSION_COOKIE_SECURE=secure_session, CSRF_COOKIE_SECURE=secure_csrf,
                SESSION_COOKIE_HTTPONLY=True, CSRF_COOKIE_HTTPONLY=False,
                SESSION_COOKIE_SAMESITE='Lax', CSRF_COOKIE_SAMESITE='Lax',
                SESSION_COOKIE_AGE=number('SESSION_COOKIE_AGE', 28800 if production else 1209600, 300),
                SESSION_SAVE_EVERY_REQUEST=False,
                SECURE_SSL_REDIRECT=redirect,
                SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https') if boolean('TRUST_PROXY', False) else None,
                SECURE_HSTS_SECONDS=number('SECURE_HSTS_SECONDS', 60 if production else 0),
                SECURE_HSTS_INCLUDE_SUBDOMAINS=boolean('SECURE_HSTS_INCLUDE_SUBDOMAINS', False),
                SECURE_HSTS_PRELOAD=boolean('SECURE_HSTS_PRELOAD', False),
                X_FRAME_OPTIONS='DENY', SECURE_CONTENT_TYPE_NOSNIFF=True,
                SECURE_REFERRER_POLICY='same-origin', PRIVATE_MEDIA_DELIVERY=delivery)
