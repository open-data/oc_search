"""
Django settings for oc_search project.
For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""
import bleach.sanitizer
from django.utils.translation import gettext_lazy as _
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'Replace_this_key_with_a_random_value!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django_celery_beat',
    'django_celery_results',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'qurl_templatetag',
    'search',
]

## Optional applications
# 'ramp',
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    "django.middleware.common.CommonMiddleware",
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'oc_search.middleware.CanadaBilingualMiddleware'
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_REPLACE_HTTPS_REFERER = True
SECURE_REFERRER_POLICY = 'unsafe-url'

ROOT_URLCONF = 'oc_search.urls'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    ('search_snippets', os.path.join(BASE_DIR, 'search', 'templates', 'snippets')),
    ('cache', os.path.join(BASE_DIR, 'cache')),
]
# ('ramp', os.path.join(BASE_DIR, 'ramp', 'viewer')),

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'static'),
                 os.path.join(BASE_DIR, 'search', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'oc_search.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

# The search application specifies a separate configuration for the main functions of the search application
# Future plugins are free to add other databaes if required but should not use the default database, or
# the default Database router defined in the db_router.py class, but should instead add their own router.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Sample PostgreSQL 
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'HOST': '127.0.0.1',
#         'NAME': 'ocs',
#         'CONN_MAX_AGE': None,
#         'PASSWORD': 'xxxxxxxxxxxx',
#         'PORT': '',
#         'USER': 'search'
#     }
# }

JSON_DOWNLOADS_ALLOWED = False

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [
    ('en', _('English')),
    ('fr', _('French')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'query_log': {
            'class': 'logging.StreamHandler',
            'formatter': 'search_term_formatter',
            'encoding': 'utf8',
        },
    },
    'formatters': {
        'search_term_formatter': {
            'format': '%(asctime)s,%(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%SZ'
        }
    },
    'loggers': {
        'search_term_logger': {
            'handlers': ['query_log'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
# Django Cache settings

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'oc_search',
    },
}
# Object in the local cache expire after this many seconds. Not recommended to be less than 60 seconds.
CACHE_LOCAL_TIMEOUT = 30

# Djagno User session settings

SESSION_ENGINE="django.contrib.sessions.backends.file"
SESSION_FILE_PATH = os.path.join(BASE_DIR, 'session')
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

#### Open Canada Search specific settings

# File cache directory used by the export search results feature. If files are served by a web server like Nginx
# or Apache, set the FILE_CACHE_URL

EXPORT_FILE_CACHE_DIR = os.path.join(BASE_DIR, 'cache')
EXPORT_FILE_CACHE_URL = "http://127.0.0.1:8000/static/cache"

# Use HTTP POST or GET for search form submission. Choices are "Post" or "Get".
# When usimg "Post" be sure to change the default APPEND_SLASH setting from True to False
HTTP_FORM_PROTOCOL = "Get"
#APPEND_SLASH = False

# Solr Search Configuration

SOLR_SERVER_URL = 'http://localhost:8983/solr'

SOLR_COLLECTION = "SolrClient_unittest"

# Application URL
# Search can either use the Hostname or a file path to determine
# language to be used. If using unique website hostnames, provide
# both the English and French host names: 
# 
# For example: 
# SEARCH_EN_HOSTNAME = 'searchme.ca'
# SEARCH_FR_HOSTNAME = 'rechercheamoi.ca'
#
# If using hostname, set SEARCH_LANG_USE_PATH = False
#
# Indicate which custom search type to use if no search type
# is provide in the URL

SEARCH_EN_HOSTNAME = 'http://127.0.0.1:8000'
SEARCH_FR_HOSTNAME = 'http://127.0.0.1:8000'
SEARCH_HOST_PATH = ''
SEARCH_LANG_USE_PATH = True
DEFAULT_SEARCH_TYPE = 'data'

# Active CDTS Version

CDTS_VERSION = 'v5_1_0'

# Limit what can be included in Markdown formatted fields

MARKDOWN_FILTER_WHITELIST_TAGS = [
    'a',
    'p',
    'code',
    'em',
    'h1', 'h2', 'h3', 'h4',
    'ul',
    'ol',
    'li',
    'br',
    'mark',
    'pre',
    'span',
    'strong',
    'table', 'thead', 'th', 'tr', 'tbody', 'td'
]
MARKDOWN_FILTER_EXTRAS = ["tables", "break-on-newline"]
# These are IN ADDITION to the attributes defined in leach.sanitizer.ALLOWED_ATTRIBUTES
MARKDOWN_FILTER_ALLOWED_ATTRIBUTES = {'span': ['title', 'class'], "a": ["href", "title", "rel"]}

ADOBE_ANALYTICS_URL = ''
GOOGLE_ANALYTICS_GTM_ID = ''
GOOGLE_ANALYTICS_PROPERTY_ID = ''
GOOGLE_ANALYTICS_GA4_ID = ''

IMPORT_EXPORT_USE_TRANSACTIONS = False

# Geoviewer Settings specifically for the Open Data Custom search
OPEN_DATA_SOLR_SERVER_URL = "http://localhost:8983/solr"
OPEN_DATA_CORE = "search_opendata"
OPEN_DATA_BASE_URL_EN = "https://open.canada.ca/data/en/dataset/"
OPEN_DATA_BASE_URL_FR = "https://ouvert.canada.ca/data/fr/dataset/"
OPEN_DATA_EN_FGP_BASE = "https://search.open.canada.ca/openmap/"
OPEN_DATA_FR_FGP_BASE = "https://rechercher.ouvert.canada.ca/carteouverte/"
OPEN_DATA_HOST_EN = "https://open.canada.ca"
OPEN_DATA_HOST_FR = "https://ouvert.canada.ca"


# Celery Congifuration

CELERY_BROKER_URL = 'redis://:<redis_password>@localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TIME_ZONE = TIME_ZONE
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7  # 1 week
# Max task time allowed in seconds
CELERYD_TIME_LIMIT = 20
# No. of Celery workers
CELERYD_CONCURRENCY = 2
# the task will report its status as ‘started’ when the task is executed by a worker.
CELERY_TASK_TRACK_STARTED = True

## Optional query logging. This feature will save query information to json file which can then
## by imported into the Search database. This can result in an exceptional amount of logging and is
## not recommended to be left on by default.

SEARCH_LOGGING_ON = False

# Log file to hold exported search logs
SEARCH_LOGGING_ARCHIVE_FILE = os.path.join(BASE_DIR, 'data', 'search_logs.log')
SEARCH_LOGGING_ARCHIVE_AFTER_X_DAYS = 7

# Used by the import_data_csv console command

IMPORT_DATA_CSV_DEFAULT_DEBUG = False
IMPORT_DATA_CSV_SOLR_INDEX_GROUP_SIZE = 10
IMPORT_DATA_CSV_BAD_DATA_DIR = os.path.join(BASE_DIR, 'bad_data')

# Canada.ca Invitation Manager

IM_ENABLED = False
