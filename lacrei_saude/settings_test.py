"""
Configurações específicas para testes - Lacrei Saúde API
=======================================================
"""

from .settings import *
import os

# Database para testes
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desabilitar migrações para acelerar testes
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Email backend para testes
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache em memória para testes
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging simplificado para testes
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['null'],
        },
    }
}

# Desabilitar debug para acelerar testes
DEBUG = False

# SECRET_KEY simples para testes
SECRET_KEY = 'test-secret-key-for-testing-only'

# Media files para testes
MEDIA_ROOT = '/tmp/lacrei_saude_test_media'

# Static files para testes
STATIC_ROOT = '/tmp/lacrei_saude_test_static'

# Configurações de password hashers mais rápidas para testes
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Timezone para testes
USE_TZ = True

# Configurações de teste específicas para JWT
from datetime import timedelta

SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
})

# Desabilitar rate limiting nos testes
RATELIMIT_ENABLE = False

# Configurações CORS para testes
CORS_ALLOW_ALL_ORIGINS = True

# Fixtures para carregar automaticamente nos testes
FIXTURE_DIRS = [
    os.path.join(BASE_DIR, 'fixtures'),
]

# Configurações específicas para coverage
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'venv', '__pycache__'
]

# Configurações para pytest-django
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Apps adicionais para testes (se houver)
INSTALLED_APPS += [
    # Apps específicos para teste podem ser adicionados aqui
]

# Middleware simplificado para testes
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Removemos middlewares de logging e rate limiting nos testes
]

# Configurações de segurança relaxadas para testes
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Configurações de arquivo
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB