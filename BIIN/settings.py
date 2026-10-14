import os
from pathlib import Path
import environ
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(BASE_DIR / '.env')


# from django.core.exceptions import ImproperlyConfigured
# from dotenv import load_dotenv

# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent
# ENV_FILE = Path(os.getenv('DJANGO_ENV_FILE', BASE_DIR / '.env'))
# # if not ENV_FILE.is_absolute():
# #     ENV_FILE = BASE_DIR / ENV_FILE
# # load_dotenv(ENV_FILE)


# # def env_bool(name, default=False):
# #     value = os.getenv(name)
# #     if value is None:
# #         return default
# #     return value.strip().lower() in {'1', 'true', 'yes', 'on'}


# # def env_list(name, default=''):
# #     return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


# # def env_int(name, default=0):
# #     try:
# #         return int(os.getenv(name, default))
# #     except (TypeError, ValueError) as error:
# #         raise ImproperlyConfigured(f'{name} must be an integer.') from error


# # def required_env(name):
# #     value = os.getenv(name)
# #     if not value:
# #         raise ImproperlyConfigured(f'{name} environment variable is required.')
# #     return value


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
DEBUG = os.getenv('DEBUG', 'False').lower() in ['1', 'true', 'yes', 'on']
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [h.strip() for h in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if h.strip()]

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
        'DIRS': ["templates"],
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


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

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
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'Asia/Dhaka')

USE_I18N = True

USE_TZ = True


STATIC_URL = os.getenv('DJANGO_STATIC_URL', 'static/')
MEDIA_URL = os.getenv('DJANGO_MEDIA_URL', 'media/')
if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / os.getenv('DJANGO_STATIC_DIR', 'static')]
else:
    STATIC_ROOT = BASE_DIR / os.getenv('DJANGO_STATIC_ROOT', 'staticfiles')
MEDIA_ROOT = BASE_DIR / os.getenv('DJANGO_MEDIA_ROOT', 'media')


EMAIL_BACKEND = os.getenv(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = os.getenv('DJANGO_DEFAULT_FROM_EMAIL', 'BIIN <noreply@biin.org.bd>')
