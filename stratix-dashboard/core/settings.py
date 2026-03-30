import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-stratix-default-key-123')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

# 🚀 FIX: Added 'stratixjm-dashboard.onrender.com' and '.onrender.com' wildcard
ALLOWED_HOSTS = ['stratix-dashboard.onrender.com', 'stratixjm-dashboard.onrender.com', '.onrender.com', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Internal Apps
    'reports',
    
    # Third-party
    'corsheaders',
    'rest_framework',
    'channels',
    'crispy_forms',
    'storages', # Required for Supabase S3 Storage
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # whitenoise for static
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'reports.context_processors.alert_processor', 
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# Database configuration (Supabase PostgreSQL)
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Use WhiteNoise for static files in production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'login'

CORS_ALLOW_ALL_ORIGINS = True

# Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Redis/Channels Configuration
REDIS_URL = config('REDIS_URL', default=None)
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    # Fallback for local development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ----------------------------------------------------------------------
# SUPABASE S3-COMPATIBLE STORAGE CONFIGURATION (Fixes vanishing files)
# ----------------------------------------------------------------------
# When debug is False (production), send files to Supabase Storage.
if not DEBUG:
    # Required parameters to be set in Render Environment
    SUPABASE_PROJECT_REF = config('SUPABASE_PROJECT_REF')
    SUPABASE_ANON_KEY = config('SUPABASE_ANON_KEY')
    SUPABASE_STORAGE_BUCKET_NAME = config('SUPABASE_STORAGE_BUCKET_NAME')

    # Django Storages (S3) Settings mapped to Supabase Storage
    AWS_ACCESS_KEY_ID = SUPABASE_ANON_KEY
    AWS_SECRET_ACCESS_KEY = SUPABASE_ANON_KEY
    AWS_STORAGE_BUCKET_NAME = SUPABASE_STORAGE_BUCKET_NAME
    
    # Supabase unique S3-compatible endpoint format
    AWS_S3_ENDPOINT_URL = f'https://{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3'
    
    # Optimization settings for Supabase
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None # Supabase handles permission via RLS, not ACLs
    AWS_S3_REGION_NAME = 'us-east-1' # dummy region often needed by boto3
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_CUSTOM_DOMAIN = f'{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3/{SUPABASE_STORAGE_BUCKET_NAME}'
    AWS_S3_USE_SSL = True

    # Critical: Set Django to use the S3 engine for media
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Files are now served directly from the Supabase public storage endpoint
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    
else:
    # Local Development Fallback
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
