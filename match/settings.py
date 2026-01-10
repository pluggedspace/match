from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev-only')
# Increase the limit to handle bulk deletions
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000 
# Debug
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ['*']

FORCE_SCRIPT_NAME = "/match"

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
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
    'storages',  # django-storages for S3
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

# Media files (S3 Storage)
# ============================================
# This works with both AWS S3 and Backblaze B2
# 
# For AWS S3:
#   AWS_ACCESS_KEY_ID = your AWS access key
#   AWS_SECRET_ACCESS_KEY = your AWS secret key
#   AWS_STORAGE_BUCKET_NAME = your-bucket-name
#   AWS_S3_REGION_NAME = us-east-1 (or your region)
#   AWS_S3_ENDPOINT_URL = (leave empty)
#
# For Backblaze B2:
#   AWS_ACCESS_KEY_ID = your B2 keyID
#   AWS_SECRET_ACCESS_KEY = your B2 applicationKey
#   AWS_STORAGE_BUCKET_NAME = your-bucket-name
#   AWS_S3_REGION_NAME = us-west-000 (or your region)
#   AWS_S3_ENDPOINT_URL = https://s3.us-west-000.backblazeb2.com
# ============================================

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')  # ✅ Uses .env
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')  # ✅ Uses .env  
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'match-bot')  # ✅ Matches .env
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ca-east-006')  # ✅ Matches .env
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)  # ✅ Uses .env

# Build the custom domain URL
if AWS_S3_ENDPOINT_URL:
    # Backblaze B2
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_ENDPOINT_URL.replace("https://", "")}'
else:
    # AWS S3
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'private'
AWS_S3_SIGNATURE_VERSION = 's3v4'

# Use S3 for media files if AWS credentials are provided
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    DEFAULT_FILE_STORAGE = 'matches.storage.MediaStorage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Fallback to local storage for development
    MEDIA_URL = "/match/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# External APIs
PLUGGEDSPACE_API_KEY = os.getenv("PLUGGEDSPACE_API_KEY", "")
PAYMENTS_API_BASE = "https://example.com/pay"
BASE_URL = "https://example.com/match"

# Telegram Bot
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY", "")

