# from pathlib import Path
# import environ

# env = environ.Env()
# BASE_DIR = Path(__file__).resolve().parent.parent
# environ.Env.read_env(BASE_DIR / '.env')


# SECRET_KEY = env('DJANGO_SECRET_KEY')
# DEBUG = env.bool('DJANGO_DEBUG', default=True)
# ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=[])
# CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

# # Application definition

# INSTALLED_APPS = [
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'home',
#     'registration',
# ]

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# ROOT_URLCONF = 'BIIN.urls'

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': ["templates"],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = 'BIIN.wsgi.application'


# # Database
# # https://docs.djangoproject.com/en/6.1/ref/settings/#databases

# DB_ENGINE = env('DJANGO_DB_ENGINE', default='sqlite3')
# DB_ENGINE = {'sqlite': 'sqlite3', 'postgres': 'postgresql'}.get(DB_ENGINE, DB_ENGINE)
# DB_BACKEND = DB_ENGINE if '.' in DB_ENGINE else f'django.db.backends.{DB_ENGINE}'
# if DB_BACKEND == 'django.db.backends.sqlite3':
#     DB_NAME = env('DJANGO_DB_NAME', default='db.sqlite3')
# else:
#     DB_NAME = env('DJANGO_DB_NAME')
# DB_OPTIONS = env.json('DJANGO_DB_OPTIONS', default={})

# if DB_BACKEND == 'django.db.backends.sqlite3':
#     if DB_NAME != ':memory:':
#         DB_NAME = BASE_DIR / DB_NAME
#     DB_OPTIONS.setdefault('timeout', env.int('SQLITE_TIMEOUT_SECONDS', default=15))

# DATABASES = {
#     'default': {
#         'ENGINE': DB_BACKEND,
#         'NAME': DB_NAME,
#         'USER': env('DJANGO_DB_USER', default=''),
#         'PASSWORD': env('DJANGO_DB_PASSWORD', default=''),
#         'HOST': env('DJANGO_DB_HOST', default=''),
#         'PORT': env('DJANGO_DB_PORT', default=''),
#         'CONN_MAX_AGE': env.int('DJANGO_DB_CONN_MAX_AGE', default=0),
#         'OPTIONS': DB_OPTIONS,
#     }
# }


# # Password validation
# # https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# # Internationalization
# # https://docs.djangoproject.com/en/6.1/topics/i18n/

# LANGUAGE_CODE = 'en-us'

# TIME_ZONE = env('DJANGO_TIME_ZONE', default='Asia/Dhaka')
# USE_I18N = True
# USE_TZ = True


# STATIC_URL = env('DJANGO_STATIC_URL', default='static/')
# MEDIA_URL = env('DJANGO_MEDIA_URL', default='media/')
# if DEBUG:
#     STATICFILES_DIRS = [BASE_DIR / env('DJANGO_STATIC_DIR', default='static')]
# else:
#     STATIC_ROOT = BASE_DIR / env('DJANGO_STATIC_ROOT', default='staticfiles')
# MEDIA_ROOT = BASE_DIR / env('DJANGO_MEDIA_ROOT', default='media')

import os
from dotenv import load_dotenv
import logging
from datetime import timedelta

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
DEBUG = os.getenv('DEBUG', 'False').lower() in ['1', 'true', 'yes', 'on']
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
# Security Settings for Production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'home',
    'registration',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'BIIN.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'BIIN.wsgi.application'

DB_ENGINE = os.getenv('DJANGO_DB_ENGINE', 'sqlite3')
if DB_ENGINE == 'sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / os.getenv('DJANGO_DB_NAME', 'db.sqlite3'),
            'OPTIONS': {
                # Wait before raising "database is locked" under concurrent writes.
                'timeout': int(os.getenv('SQLITE_TIMEOUT_SECONDS', '15')),
            },
        }
    }
else:
    DATABASES = {
        'default': {
        'ENGINE': f'django.db.backends.{DB_ENGINE}',
        'NAME': os.getenv('DJANGO_DB_NAME'),
        'USER': os.getenv('DJANGO_DB_USER'),
        'PASSWORD': os.getenv('DJANGO_DB_PASSWORD'),
        'HOST': os.getenv('DJANGO_DB_HOST'),
        'PORT': os.getenv('DJANGO_DB_PORT'),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True


STATIC_URL = os.getenv('DJANGO_STATIC_URL', 'static/')
MEDIA_URL = os.getenv('DJANGO_MEDIA_URL', 'media/')
if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / os.getenv('DJANGO_STATIC_DIR', 'static')]
else:
    STATIC_ROOT = BASE_DIR / os.getenv('DJANGO_STATIC_ROOT', 'staticfiles')
MEDIA_ROOT = BASE_DIR / os.getenv('DJANGO_MEDIA_ROOT', 'media')


# Third-party integrations
TURNSTILE_SITE_KEY = os.getenv('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY', '')
TURNSTILE_REQUIRE_AUTH = os.getenv('TURNSTILE_REQUIRE_AUTH', 'true').lower() in ['1', 'true', 'yes', 'on']

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
