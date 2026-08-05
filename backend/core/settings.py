"""
Django settings for core project.

https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from pathlib import Path

from decouple import AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

config = AutoConfig(search_path=str(REPO_ROOT))

SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "users",
    "catalog",
    "logistica",
    "tracking",
    "transportista",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("APP_DB_NAME"),
        "USER": config("APP_DB_USER"),
        "PASSWORD": config("APP_DB_PASSWORD"),
        "HOST": config("APP_DB_HOST"),
        "PORT": config("APP_DB_PORT", cast=int),
        "CONN_MAX_AGE": config("CONN_MAX_AGE", default=60, cast=int),
        "CONN_HEALTH_CHECKS": True,
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "api/static/"

AUTH_USER_MODEL = "users.User"


# Sesión y CSRF
#
# El secreto de CSRF vive en la sesión, no en una cookie propia: así el browser guarda
# una sola cookie y va HttpOnly. El token viaja en el body de los DTOs de auth y la SPA
# lo manda en el header X-CSRFToken.

CSRF_USE_SESSIONS = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=60 * 60 * 8, cast=int)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="http://localhost", cast=Csv()
)


# Integraciones externas

ORS_API_KEY = config("ORS_API_KEY", default="")
ORS_SNAP_RADIUS_M = config("ORS_SNAP_RADIUS_M", default=350, cast=int)

# Sin valor, el endpoint de ingesta rechaza todo.
INGEST_API_KEY = config("INGEST_API_KEY", default="")

TZ_OPERACION = config("TZ_OPERACION", default="America/Argentina/Buenos_Aires")


# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {"level": config("SQL_LOG_LEVEL", default="WARNING")},
        "catalog": {"level": "INFO", "propagate": True},
        "logistica": {"level": "INFO", "propagate": True},
        "tracking": {"level": "INFO", "propagate": True},
        "transportista": {"level": "INFO", "propagate": True},
        "users": {"level": "INFO", "propagate": True},
    },
}
