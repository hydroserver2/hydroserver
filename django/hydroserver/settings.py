import environ

from pathlib import Path
from uuid import UUID
from urllib.parse import urlparse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.exceptions import ImproperlyConfigured
from celery.schedules import crontab


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"

if env_file.exists():
    environ.Env.read_env(env_file)


# Security & Debug

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    "SECRET_KEY",
    default="django-insecure-zw@4h#ol@0)5fxy=ib6(t&7o4ot9mzvli*d-wd=81kjxqc!5w4",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)


# Networking & Proxy

PROXY_BASE_URL = env.str("PROXY_BASE_URL", default="http://127.0.0.1:8000")

TRUSTED_LOCAL_ENVIRONMENT = env.bool(
    "TRUSTED_LOCAL_ENVIRONMENT",
    default=urlparse(PROXY_BASE_URL).hostname in {"127.0.0.1", "localhost"}
)

WEB_CLIENT_URL = env.str(
    "WEB_CLIENT_URL",
    default=(
        f"http://{urlparse(PROXY_BASE_URL).hostname}:1203"
        if TRUSTED_LOCAL_ENVIRONMENT else PROXY_BASE_URL
    ),
)

if not TRUSTED_LOCAL_ENVIRONMENT and SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("SECRET_KEY must be set for deployed instances")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
ALLOWED_HOSTS.append(urlparse(PROXY_BASE_URL).hostname)

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = TRUSTED_LOCAL_ENVIRONMENT
CORS_URLS_REGEX = r"^/$|^/(api|identity|\.well-known|media|static)/.*$"

CORS_EXPOSE_HEADERS = [
    "X-Total-Pages",
    "X-Total-Count",
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env.list("CSRF_TRUSTED_ORIGINS", default=[PROXY_BASE_URL])
    if origin.strip()
]

CSRF_COOKIE_SECURE = urlparse(PROXY_BASE_URL).scheme == "https"
SESSION_COOKIE_SECURE = urlparse(PROXY_BASE_URL).scheme == "https"

NOINDEX = env.bool("NOINDEX", default=False)


# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.idp.oidc",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.orcid",
    "allauth.socialaccount.providers.openid_connect",
    "core.iam.auth.providers.hydroshare",
    "core.iam.auth.providers.orcidsandbox",
    "corsheaders",
    "sensorthings.versions.v1_1",
    "sensorthings.versions.v1_1.extensions.dataarray",
    "storages",
    "django_celery_beat",
    "django_tailwind_cli",
    "interfaces.api.apps.ApiConfig",
    "interfaces.web.apps.WebConfig",
    "interfaces.actions.apps.ActionsConfig",
    "core.iam.apps.IamConfig",
    "core.sta.apps.StaConfig",
    "core.web.apps.WebConfig",
    "processing.orchestration.apps.OrchestrationConfig",
    "processing.etl.apps.EtlConfig",
    "processing.products.apps.ProductsConfig",
    "processing.monitoring.apps.MonitoringConfig",
    "processing.quality.apps.QualityConfig",
    "django.contrib.admin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "hydroserver.middleware.CloudHealthCheckMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",
    "core.web.middleware.NoIndexMiddleware",
]

if TRUSTED_LOCAL_ENVIRONMENT:
    MIDDLEWARE.remove("django.middleware.csrf.CsrfViewMiddleware")

ROOT_URLCONF = "hydroserver.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hydroserver.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": env.db(
        default="postgresql://hsdbadmin:admin@127.0.0.1:5432/hydroserver"
    )
}

DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=0)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env.bool(
    "CONN_HEALTH_CHECKS", default=True
)

DATABASES["default"].setdefault("OPTIONS", {}).update(
    {
        "application_name": "HydroServer",
        "pool": {
            "min_size": env.int("DB_POOL_MIN_SIZE", default=5),
            "max_size": env.int("DB_POOL_MAX_SIZE", default=10),
            "timeout": env.int("DB_POOL_TIMEOUT", default=60),
        },
    }
)

if env.bool("SSL_REQUIRED", default=False):
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"


# Caching

if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "hydroserver-dev-cache",
        }
    }

PUBLIC_THING_MARKERS_CACHE_TIMEOUT = env.int(
    "PUBLIC_THING_MARKERS_CACHE_TIMEOUT", default=300
)


# Site and Session

SITE_ID = 1

SESSION_COOKIE_NAME = env.str("SESSION_COOKIE_NAME", default="hs_session")
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=86400)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# Account and Access Control

AUTH_USER_MODEL = "iam.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SERVICE_ACCOUNT_EMAIL_DOMAIN = env.str(
    "SERVICE_ACCOUNT_EMAIL_DOMAIN", default="hydroserver.local"
)

ACCOUNT_SIGNUP_ENABLED = env.bool("ACCOUNT_SIGNUP_ENABLED", default=True)
ACCOUNT_OWNERSHIP_ENABLED = env.bool("ACCOUNT_OWNERSHIP_ENABLED", default=True)
ACCOUNT_RATE_LIMITS = env.json(
    "ACCOUNT_RATE_LIMITS", default={} if not TRUSTED_LOCAL_ENVIRONMENT else False
)

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_SIGNUP_FORM_CLASS = "core.iam.auth.forms.UserSignupForm"

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = True
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = True

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

ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = urlparse(PROXY_BASE_URL).scheme

LOGIN_REDIRECT_URL = WEB_CLIENT_URL
LOGOUT_REDIRECT_URL = WEB_CLIENT_URL

ACCOUNT_ADAPTER = "core.iam.auth.adapters.AccountAdapter"


# Social Account

SOCIALACCOUNT_SIGNUP_ONLY = env.bool("SOCIALACCOUNT_SIGNUP_ONLY", default=False)

SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "mandatory"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True

SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_STORE_TOKENS = True


# OpenID Connect Identity Provider

IDP_OIDC_ENABLED = env.bool("IDP_OIDC_ENABLED", default=True)

IDP_OIDC_PRIVATE_KEY_FILE = env.str("IDP_OIDC_PRIVATE_KEY_FILE", default="")
IDP_OIDC_PRIVATE_KEY = (
    Path(IDP_OIDC_PRIVATE_KEY_FILE).read_text()
    if IDP_OIDC_PRIVATE_KEY_FILE
    else env.str("IDP_OIDC_PRIVATE_KEY", default="")
)

if not IDP_OIDC_PRIVATE_KEY and TRUSTED_LOCAL_ENVIRONMENT:
    _dev_key_path = BASE_DIR / "dev_oidc_private_key.pem"
    if not _dev_key_path.exists():
        _dev_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _dev_key_path.write_bytes(
            _dev_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        _dev_key_path.chmod(0o600)
    IDP_OIDC_PRIVATE_KEY = _dev_key_path.read_text()

if IDP_OIDC_ENABLED and not TRUSTED_LOCAL_ENVIRONMENT and not IDP_OIDC_PRIVATE_KEY:
    raise ImproperlyConfigured(
        "IDP_OIDC_PRIVATE_KEY must be set for deployed instances with "
        "IDP_OIDC_ENABLED"
    )

IDP_OIDC_ACCESS_TOKEN_EXPIRES_IN = env.int("IDP_OIDC_ACCESS_TOKEN_EXPIRES_IN", default=3600)
IDP_OIDC_ROTATE_REFRESH_TOKEN = env.bool("IDP_OIDC_ROTATE_REFRESH_TOKEN", default=True)
IDP_OIDC_ADAPTER = "core.iam.auth.oidc_adapter.HydroServerOIDCAdapter"


# Email

EMAIL_CONFIG = env.email("SMTP_URL", default="consolemail://")

EMAIL_BACKEND = EMAIL_CONFIG["EMAIL_BACKEND"]
EMAIL_HOST = EMAIL_CONFIG["EMAIL_HOST"]
EMAIL_PORT = EMAIL_CONFIG["EMAIL_PORT"]
EMAIL_HOST_USER = EMAIL_CONFIG["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = EMAIL_CONFIG["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = EMAIL_CONFIG.get("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = EMAIL_CONFIG.get("EMAIL_USE_SSL", False)

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="webmaster@localhost")


# Storage

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

STORAGES = {
    "default": {
        "BACKEND": env.str(
            "MEDIA_STORAGE_BACKEND",
            default="django.core.files.storage.FileSystemStorage",
        ),
        "OPTIONS": env.json(
            "MEDIA_STORAGE_OPTIONS", default={"location": str(BASE_DIR / "media")}
        ),
    },
    "staticfiles": {
        "BACKEND": env.str(
            "STATIC_STORAGE_BACKEND",
            default="django.contrib.staticfiles.storage.StaticFilesStorage",
        ),
        "OPTIONS": env.json(
            "STATIC_STORAGE_OPTIONS", default={"location": str(BASE_DIR / "static")}
        ),
    },
}

MEDIA_STORAGE_IS_LOCAL = (
    STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"
)
STATIC_STORAGE_IS_LOCAL = (
    STORAGES["staticfiles"]["BACKEND"] == "django.contrib.staticfiles.storage.StaticFilesStorage"
)

TAILWIND_CLI_VERSION = "4.1.3"
TAILWIND_CLI_SRC_CSS = "static/css/input.css"


# Celery

CELERY_ENABLED = env.bool("CELERY_ENABLED", default=True)
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = None
CELERY_BROKER_HEARTBEAT = 10
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_keepalive": True,
    "retry_on_timeout": True,
    "socket_timeout": 30,
}

TASK_RUN_RETENTION_DAYS = env.int("TASK_RUN_RETENTION_DAYS", default=7)
TASK_RUN_CLEANUP_CRONTAB = env.str(
    "TASK_RUN_CLEANUP_CRONTAB", default="0 3 * * *"
).split()

CELERY_BEAT_SCHEDULE = {
    "cleanup_task_runs": {
        "task": "processing.orchestration.tasks.cleanup_task_runs",
        "schedule": crontab(
            minute=TASK_RUN_CLEANUP_CRONTAB[0],
            hour=TASK_RUN_CLEANUP_CRONTAB[1],
            day_of_month=TASK_RUN_CLEANUP_CRONTAB[2],
            month_of_year=TASK_RUN_CLEANUP_CRONTAB[3],
            day_of_week=TASK_RUN_CLEANUP_CRONTAB[4],
        ),
        "args": (TASK_RUN_RETENTION_DAYS,),
    },
}


# Logging

LOG_FORMAT = env.str("LOG_FORMAT", default="standard")

LOGGING_FORMATTERS = {}

if LOG_FORMAT == "json":
    LOGGING_FORMATTERS["standard"] = {
        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
        "format": "%(levelname)s %(run_id)s %(name)s %(message)s",
        "rename_fields": {"levelname": "level"},
    }
else:
    LOGGING_FORMATTERS["standard"] = {
        "format": "%(levelname)s %(run_id)s %(name)s %(message)s",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "run_id": {
            "()": "processing.orchestration.logging.RunIdFilter",
        },
    },
    "formatters": LOGGING_FORMATTERS,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["run_id"],
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# API

ANON_THROTTLE_RATE = env.str("ANON_THROTTLE_RATE", default="20/s")
AUTH_THROTTLE_RATE = env.str("AUTH_THROTTLE_RATE", default="20/s")


# SensorThings

SENSORTHINGS_V1_1_SERVICE_URL = f"{PROXY_BASE_URL}/api/sensorthings"
SENSORTHINGS_V1_1_BACKEND_ADAPTER = "interfaces.sensorthings.adapter.HydroServerAdapter"
SENSORTHINGS_V1_1_DEFAULT_AUTH_HANDLER = [
    "interfaces.auth.security.session_auth",
    "interfaces.auth.security.oidc_auth",
    "interfaces.auth.security.basic_auth",
    "interfaces.auth.security.apikey_auth",
    "interfaces.auth.security.anonymous_auth",
]
SENSORTHINGS_V1_1_ID_TYPE = UUID
SENSORTHINGS_V1_1_ID_DELIMITER = "'"
SENSORTHINGS_V1_1_MAX_TOP = env.int("SENSORTHINGS_V1_1_MAX_TOP", default=1000)
SENSORTHINGS_V1_1_PROPERTIES_SCHEMAS = {
    "Things": "interfaces.sensorthings.schemas.ThingProperties",
    "Datastreams": "interfaces.sensorthings.schemas.DatastreamProperties",
    "Locations": "interfaces.sensorthings.schemas.LocationProperties",
    "ObservedProperties": "interfaces.sensorthings.schemas.ObservedPropertyProperties",
    "Sensors": "interfaces.sensorthings.schemas.SensorProperties",
}
SENSORTHINGS_V1_1_SENSOR_METADATA_ENCODING_TYPE_SCHEMA = "interfaces.sensorthings.schemas.SensorMetadata"
SENSORTHINGS_V1_1_SENSOR_METADATA_ENCODING_TYPE_VALUE_LITERAL = "interfaces.sensorthings.schemas.sensorEncodingTypes"


# End-to-End Testing

E2E_TESTING = env.bool("E2E_TESTING", default=False)
E2E_CONTROL_TOKEN = env.str("E2E_CONTROL_TOKEN", default="")

if E2E_TESTING:
    # Browser scenarios create several short-lived users per test. The fast
    # hasher keeps that setup inexpensive and is never enabled in a normal
    # deployment.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
