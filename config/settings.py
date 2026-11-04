import os
import re
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
ENVIRONMENT = os.getenv("DJANGO_ENV", "development")
if os.getenv("VERCEL") and ENVIRONMENT != "production":
    raise ImproperlyConfigured("Vercel requires explicit DJANGO_ENV=production")
if ENVIRONMENT not in {"development", "production"}:
    raise ImproperlyConfigured("DJANGO_ENV must be development or production")
DEBUG = ENVIRONMENT == "development"
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-insecure-key")
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
SITE_URL_CONFIGURED = bool(os.getenv("SITE_URL"))
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "")
try:
    URLValidator(schemes=["http", "https"])(SITE_URL)
    site_parts = urlparse(SITE_URL)
    if (
        site_parts.username
        or site_parts.password
        or site_parts.query
        or site_parts.fragment
        or site_parts.path not in {"", "/"}
        or len(SITE_URL) > 250
    ):
        raise ValueError
except (ValueError, ValidationError):
    raise ImproperlyConfigured("SITE_URL must be an HTTP(S) origin without credentials, path or query")
database_url = os.getenv("DATABASE_URL", "")
if not DEBUG:
    for variable in ("SECRET_KEY", "DATABASE_URL", "ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", "SITE_URL"):
        if not os.getenv(variable):
            raise ImproperlyConfigured(f"Production requires {variable}")
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("replace-", "development-")):
        raise ImproperlyConfigured("Production requires a strong unique SECRET_KEY")
    if urlparse(database_url).scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("Production requires PostgreSQL")
    if not SITE_URL.startswith("https://") or any(not x.startswith("https://") for x in CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured("Production origins must use HTTPS")
    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Production hosts must be explicit")
    if any(
        not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?", host) or host.startswith(".")
        for host in ALLOWED_HOSTS
    ):
        raise ImproperlyConfigured("Production hosts must be explicit DNS names")
    for value in CSRF_TRUSTED_ORIGINS:
        parsed = urlparse(value)
        if (
            parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or not parsed.hostname
            or "*" in value
        ):
            raise ImproperlyConfigured("CSRF origins must be explicit HTTPS origins")
DATABASES = {
    "default": dj_database_url.parse(database_url, conn_max_age=0, ssl_require=not DEBUG)
    if database_url
    else {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "catalog.middleware.SecurityBoundaries",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "catalog.context.library_context",
            ]
        },
    }
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation." + name}
    for name in [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
]
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ur", "اردو"), ("ar", "العربية")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True
TIME_ZONE = "Asia/Karachi"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "0")) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv("VERCEL") == "1" else None
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# A single complete snapshot must fit these bounds; exceeding any limit is an error.
OFFLINE_MAX_EDITIONS = 5000
OFFLINE_MAX_COPIES = 10000
OFFLINE_MAX_BYTES = 20 * 1024 * 1024

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"]["OPTIONS"].update({"connect_timeout": 5})
    if not DEBUG:
        DATABASES["default"]["OPTIONS"]["sslmode"] = "verify-full"
        DATABASES["default"]["OPTIONS"]["sslrootcert"] = "system"

DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 300

# Do not send request paths, SQL, exception text or borrower form values to logs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"safe": {"format": "%(levelname)s application event"}},
    "filters": {"private": {"()": "catalog.middleware.PrivateLogFilter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe", "filters": ["private"]}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
