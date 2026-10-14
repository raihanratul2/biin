from pathlib import Path
import environ

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')


SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

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

DB_ENGINE = env('DJANGO_DATABASE_ENGINE', default='sqlite')
if DB_ENGINE in ('sqlite', 'sqlite3'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / env('DJANGO_DATABASE_NAME', default='db.sqlite3'),
            'OPTIONS': {
                # Wait before raising "database is locked" under concurrent writes.
                'timeout': env.int('SQLITE_TIMEOUT_SECONDS', default=15),
            },
        }
    }
elif DB_ENGINE in ('postgresql', 'postgres'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('POSTGRES_DB'),
            'USER': env('POSTGRES_USER'),
            'PASSWORD': env('POSTGRES_PASSWORD'),
            'HOST': env('POSTGRES_HOST', default='localhost'),
            'PORT': env('POSTGRES_PORT', default='5432'),
            'CONN_MAX_AGE': env.int('POSTGRES_CONN_MAX_AGE', default=60),
            'OPTIONS': {'sslmode': env('POSTGRES_SSLMODE', default='prefer')},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': f'django.db.backends.{DB_ENGINE}',
            'NAME': env('DJANGO_DATABASE_NAME'),
            'USER': env('DJANGO_DB_USER', default=''),
            'PASSWORD': env('DJANGO_DB_PASSWORD', default=''),
            'HOST': env('DJANGO_DB_HOST', default=''),
            'PORT': env('DJANGO_DB_PORT', default=''),
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

TIME_ZONE = env('DJANGO_TIME_ZONE', default='Asia/Dhaka')

USE_I18N = True

USE_TZ = True


STATIC_URL = env('DJANGO_STATIC_URL', default='static/')
MEDIA_URL = env('DJANGO_MEDIA_URL', default='media/')
if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / env('DJANGO_STATIC_DIR', default='static')]
else:
    STATIC_ROOT = BASE_DIR / env('DJANGO_STATIC_ROOT', default='staticfiles')
MEDIA_ROOT = BASE_DIR / env('DJANGO_MEDIA_ROOT', default='media')


EMAIL_BACKEND = env(
    'DJANGO_EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = env('DJANGO_DEFAULT_FROM_EMAIL', default='BIIN <noreply@biin.org.bd>')
