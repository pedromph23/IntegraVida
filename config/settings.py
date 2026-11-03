"""
Django settings for config project — IntegraVida.

Detecta el entorno automáticamente:
- Local (no existe RENDER): usa .env + Postgres local + DEBUG=True
- Render (existe RENDER): usa Supabase + DEBUG=False + WhiteNoise
"""

from pathlib import Path
import os
import sys

from django.core.exceptions import ImproperlyConfigured
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # No-op si no existe (Render)

# ─── Detección de entorno ─────────────────────────────────────────────
# Render inyecta la variable 'RENDER' automáticamente en todos sus servicios.
IS_PRODUCTION = "RENDER" in os.environ


# ─── Seguridad base (§13) ─────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY no está definida. Configúrala en .env (local) "
        "o en Environment Variables (Render)."
    )

FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")
TILE_SERVER_URL = os.environ.get("TILE_SERVER_URL", "")
TILE_SERVER_ATTRIBUTION = os.environ.get("TILE_SERVER_ATTRIBUTION", "")

# DEBUG: True en local, False en Render (salvo override explícito)
DEBUG = not IS_PRODUCTION and os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

# ALLOWED_HOSTS: distintos defaults según entorno
if IS_PRODUCTION:
    _default_hosts = ".onrender.com"
else:
    _default_hosts = "localhost,127.0.0.1,[::1]"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", _default_hosts).split(",")
    if h.strip()
]


# ─── Apps (§5, §12.3) ─────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'apps.usuarios.apps.UsuariosConfig',
    'apps.organizaciones.apps.OrganizacionesConfig',
    'apps.auditoria.apps.AuditoriaConfig',
    'apps.territorio.apps.TerritorioConfig',
    'apps.emergencias.apps.EmergenciasConfig',
    'apps.refugios.apps.RefugiosConfig',
    'apps.hospitales.apps.HospitalesConfig',
    'apps.pacientes.apps.PacientesConfig',
    'apps.triaje.apps.TriajeConfig',
    'apps.derivaciones.apps.DerivacionesConfig',
    'apps.inventario.apps.InventarioConfig',
    'apps.reportes.apps.ReportesConfig',
    'apps.configuracion.apps.ConfiguracionConfig',
    'frontend',
]


# ─── MIDDLEWARE (WhiteNoise solo en producción) ───────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]
if IS_PRODUCTION:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'frontend.middleware.SecurityHeadersMiddleware',
    'frontend.middleware.AdminSecurityMiddleware',
    'frontend.middleware.AdminMFARequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'frontend.context_processors.map_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ─── Base de datos ────────────────────────────────────────────────────
# LOCAL: usa .env (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
# RENDER: usa DATABASE_URL (Supabase)

if IS_PRODUCTION:
    # ── Producción: Supabase vía DATABASE_URL ──
    if not os.environ.get("DATABASE_URL"):
        raise ImproperlyConfigured(
            "En producción (Render) DEBES configurar DATABASE_URL. "
            "Copia la connection string de Supabase en Environment Variables."
        )
    
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    
    # Forzar PostGIS (Supabase da URL postgresql://)
    if 'postgres' in DATABASES['default']['ENGINE']:
        DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
        # PostGIS de Supabase vive en el esquema 'extensions'
        options = DATABASES['default'].get('OPTIONS', {})
        options['options'] = '-c search_path=public,extensions'
        DATABASES['default']['OPTIONS'] = options

else:
    # ── Local: Postgres local del .env (como siempre) ──
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': os.environ.get('DB_NAME', 'integravida_db'),
            'USER': os.environ.get(
                'DB_USER_APP', os.environ.get('DB_USER', 'integravida')
            ),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }


# ─── Autenticación (§13) ──────────────────────────────────────────────
AUTH_USER_MODEL = "usuarios.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = "/panel/login/"
LOGIN_REDIRECT_URL = "/panel/"
LOGOUT_REDIRECT_URL = "/panel/login/"


# ─── i18n (§14) ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True


# ─── Estáticos y media ───────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise solo en producción (en local, runserver sirve estáticos)
if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ─── DRF (§6.3, §17) ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'] + (
        ['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []
    ),
}


# ─── Uploads, Email, Logging ─────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend",
)

LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── Endurecimiento en producción (§19) ──────────────────────────────
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'


# ─── CSRF_TRUSTED_ORIGINS (defaults por entorno) ─────────────────────
if IS_PRODUCTION:
    _default_csrf = "https://*.onrender.com"
else:
    _default_csrf = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", _default_csrf).split(",")
    if origin.strip()
]


# ─── Admin oculto (§7.1) ─────────────────────────────────────────────
INTEGRAVIDA_ADMIN_SLUG = os.environ.get("INTEGRAVIDA_ADMIN_SLUG", "").strip()

if not INTEGRAVIDA_ADMIN_SLUG:
    if not IS_PRODUCTION:
        # Local: slug de desarrollo predecible
        INTEGRAVIDA_ADMIN_SLUG = "dev-admin-fallback"
    else:
        raise ImproperlyConfigured(
            "INTEGRAVIDA_ADMIN_SLUG es obligatorio en producción. "
            "Genera uno con: python -c \"import secrets; print(secrets.token_urlsafe(24))\""
        )

_SLUG_PROHIBIDOS = {"admin", "administracion", "panel", "gestion", "staff"}
if INTEGRAVIDA_ADMIN_SLUG in _SLUG_PROHIBIDOS:
    raise ImproperlyConfigured(
        f"INTEGRAVIDA_ADMIN_SLUG no puede ser '{INTEGRAVIDA_ADMIN_SLUG}' (predecible)."
    )


# ─── MFA del admin (F4.b) ────────────────────────────────────────────
ADMIN_MFA_REQUIRED = os.environ.get(
    "ADMIN_MFA_REQUIRED",
    "false" if not IS_PRODUCTION else "true",
).lower() == "true"


# ─── Password hashers (F5.a perf) ─────────────────────────────────────
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]