from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev-only')

# Debug
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ['api.pluggedspace.org', 'match-web', 'localhost', '127.0.0.1']

FORCE_SCRIPT_NAME = "/match"

CSRF_TRUSTED_ORIGINS = [
    "https://api.pluggedspace.org",
]

USE_X_FORWARDED_HOST = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_PATH = "/match/"
CSRF_COOKIE_PATH = "/match/"
SESSION_COOKIE_NAME = 'match_sessionid'
CSRF_COOKIE_NAME = 'match_csrftoken'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'matches.apps.MatchConfig',
    'rest_framework',
    'telegrambot',
    'backup',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'matches.subscriptions.middleware.SubscriptionMiddleware',
]

ROOT_URLCONF = 'match.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'match.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'matchdb'),
        'USER': os.getenv('POSTGRES_USER', 'matchuser'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'matchpass123'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
USE_TZ = True
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True

# Static files
STATIC_URL = "/match/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = "/match/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# External APIs
PLUGGEDSPACE_API_KEY = "1b8d4356453b69302d8706e305d728fa190ff826bfe896f14b98d6dd2ab3c51c"
PAYMENTS_API_BASE = "https://payments.pluggedspace.org/api/payments"
BASE_URL = "https://api.pluggedspace.org/match"

# Telegram Bot - ✅ FIXED
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY", "d9058fe5d7671ebfaa31e7bdfd3613b5faffd876d2ed2cdf2264a9035077409e")