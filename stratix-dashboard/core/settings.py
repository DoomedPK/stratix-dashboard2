import os
from pathlib import Path
from import_export.formats.base_formats import XLSX, CSV
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Use environment variables for sensitive data
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev-only')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Clean Allowed Hosts and include your custom domains
raw_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,stratixjm-dashboard.onrender.com,dashboard.stratixjm.com')
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(',') if host.strip()]
# We also append a wildcard for render just in case Render routes it internally
ALLOWED_HOSTS.append('.onrender.com')

INSTALLED_APPS = [
    'jazzmin',
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'import_export', 
    'reports',
    'channels',
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

# Database configuration for Supabase (PostgreSQL)
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        # Reuses connections for 60 seconds to stop Supabase from overloading
        conn_max_age=60, 
        ssl_require=True 
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

IMPORT_EXPORT_FORMATS = [XLSX, CSV]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = '/accounts/login/'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ---------------------------------------------------------
# RENDER PROXY FIX (Tells Django to trust Render's HTTPS)
# ---------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------
# WILDCARD CSRF FIX
# ---------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
    "https://*.stratixjm.com",
    "http://127.0.0.1",
    "http://localhost"
]

# ---------------------------------------------------------
# PRODUCTION SECURITY SETTINGS
# ---------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    # HSTS Settings
    SECURE_HSTS_SECONDS = 31536000 # 1 Year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------
# JAZZMIN CONFIGURATION
# ---------------------------------------------------------
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
    
    # 1. FIX: Allows the menu to collapse dynamically so forms fit on the screen
    "navigation_expanded": False,
    
    # 2. FIX: Turns off the experimental customizer to prevent layout glitches
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
