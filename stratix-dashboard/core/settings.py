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

# Hosts that are allowed to display the site
ALLOWED_HOSTS = ['stratix-dashboard.onrender.com', 'stratixjm-dashboard.onrender.com', '.onrender.com', 'localhost', '127.0.0.1']

# Domains trusted to submit forms and passwords
CSRF_TRUSTED_ORIGINS = [
    'https://stratix-dashboard.onrender.com',
    'https://stratixjm-dashboard.onrender.com',
]

# Application definition
INSTALLED_APPS = [
    'jazzmin', # 🚀 FIX: This MUST be the very first app to inject the custom UI
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
    'crispy_bootstrap5',
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
                'reports.context_processors.live_alerts', 
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# Database configuration (Supabase PostgreSQL)
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')),
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'login'

CORS_ALLOW_ALL_ORIGINS = True
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Redis/Channels Configuration
REDIS_URL = config('REDIS_URL', default=None)
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {"hosts": [REDIS_URL]},
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

# ----------------------------------------------------------------------
# SUPABASE S3-COMPATIBLE STORAGE CONFIGURATION 
# ----------------------------------------------------------------------
if not DEBUG:
    SUPABASE_PROJECT_REF = config('SUPABASE_PROJECT_REF', default='')
    SUPABASE_ANON_KEY = config('SUPABASE_ANON_KEY', default='')
    SUPABASE_STORAGE_BUCKET_NAME = config('SUPABASE_STORAGE_BUCKET_NAME', default='site-photos')

    if SUPABASE_PROJECT_REF and SUPABASE_ANON_KEY:
        AWS_ACCESS_KEY_ID = SUPABASE_ANON_KEY
        AWS_SECRET_ACCESS_KEY = SUPABASE_ANON_KEY
        AWS_STORAGE_BUCKET_NAME = SUPABASE_STORAGE_BUCKET_NAME
        AWS_S3_ENDPOINT_URL = f'https://{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/s3'
        AWS_S3_FILE_OVERWRITE = False
        AWS_DEFAULT_ACL = None 
        AWS_S3_REGION_NAME = 'us-east-1' 
        AWS_S3_SIGNATURE_VERSION = 's3v4'
        AWS_S3_CUSTOM_DOMAIN = f'{SUPABASE_PROJECT_REF}.supabase.co/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET_NAME}'
        AWS_S3_USE_SSL = True

        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ----------------------------------------------------------------------
# 🚀 FIX: JAZZMIN ADMIN UI CUSTOMIZATION
# ----------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Stratix Admin",
    "site_header": "Stratix",
    "site_brand": "STRATIX COMMAND",
    "site_logo": "images/stratix-logo.png",
    "welcome_sign": "Welcome to the Stratix Global Command Center",
    "copyright": "Stratix Ltd",
    "search_model": ["reports.Site", "auth.User"],
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Dashboard", "url": "dashboard_home"},
        {"model": "auth.User"},
    ],
    "usermenu_links": [
        {"name": "My Account", "url": "/admin/auth/user/", "icon": "fas fa-user-circle"},
    ],
    "show_sidebar": True,
    "navigation_expanded": False,
    "show_ui_builder": False,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "reports.Client": "fas fa-building",
        "reports.Project": "fas fa-project-diagram",
        "reports.Site": "fas fa-tower-cell",
        "reports.Report": "fas fa-file-invoice",
        "reports.SitePhoto": "fas fa-camera",
        "reports.ActivityAlert": "fas fa-bell",
        "reports.UserProfile": "fas fa-id-card",
        "reports.SiteIssue": "fas fa-exclamation-triangle",
    },
    "order_with_respect_to": ["reports", "auth"],
}

JAZZMIN_UI_TWEAKS = {
    "navbar": "navbar-dark", 
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
}
