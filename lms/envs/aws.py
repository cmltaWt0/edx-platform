"""
This is the default template for our main set of AWS servers. This does NOT
cover the content machines, which use content.py

Common traits:
* Use memcached, and cache-backed sessions
* Use a MySQL 5.1 database
"""
import json

from .common import *
from logsettings import get_logger_config
import os

# specified as an environment variable.  Typically this is set
# in the service's upstart script and corresponds exactly to the service name.
# Service variants apply config differences via env and auth JSON files,
# the names of which correspond to the variant.
SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)

# when not variant is specified we attempt to load an unvaried
# config set.
CONFIG_PREFIX = ""

if SERVICE_VARIANT:
    CONFIG_PREFIX = SERVICE_VARIANT + "."


################### ALWAYS THE SAME ################################
DEBUG = False
TEMPLATE_DEBUG = False

EMAIL_BACKEND = 'django_ses.SESBackend'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# Enable Berkeley forums
MITX_FEATURES['ENABLE_DISCUSSION_SERVICE'] = True

# IMPORTANT: With this enabled, the server must always be behind a proxy that
# strips the header HTTP_X_FORWARDED_PROTO from client requests. Otherwise,
# a user can fool our server into thinking it was an https connection.
# See
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
# for other warnings.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

################# NON-SECURE ENV CONFIG ##############################
# Things like server locations, ports, etc.

with open(ENV_ROOT / CONFIG_PREFIX + "env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

SITE_NAME = ENV_TOKENS['SITE_NAME']
SESSION_COOKIE_DOMAIN = ENV_TOKENS.get('SESSION_COOKIE_DOMAIN')

BOOK_URL = ENV_TOKENS['BOOK_URL']
MEDIA_URL = ENV_TOKENS['MEDIA_URL']
LOG_DIR = ENV_TOKENS['LOG_DIR']

CACHES = ENV_TOKENS['CACHES']

for feature, value in ENV_TOKENS.get('MITX_FEATURES', {}).items():
    MITX_FEATURES[feature] = value

WIKI_ENABLED = ENV_TOKENS.get('WIKI_ENABLED', WIKI_ENABLED)
local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL', 'INFO')

LOGGING = get_logger_config(LOG_DIR,
                            logging_env=ENV_TOKENS['LOGGING_ENV'],
                            syslog_addr=(ENV_TOKENS['SYSLOG_SERVER'], 514),
                            local_loglevel=local_loglevel,
                            debug=False,
                            service_variant=SERVICE_VARIANT)

COURSE_LISTINGS = ENV_TOKENS.get('COURSE_LISTINGS', {})
SUBDOMAIN_BRANDING = ENV_TOKENS.get('SUBDOMAIN_BRANDING', {})
VIRTUAL_UNIVERSITIES = ENV_TOKENS.get('VIRTUAL_UNIVERSITIES', [])
COMMENTS_SERVICE_URL = ENV_TOKENS.get("COMMENTS_SERVICE_URL", '')
COMMENTS_SERVICE_KEY = ENV_TOKENS.get("COMMENTS_SERVICE_KEY", '')
CERT_QUEUE = ENV_TOKENS.get("CERT_QUEUE", 'test-pull')

############################## SECURE AUTH ITEMS ###############
# Secret things: passwords, access keys, etc.
with open(ENV_ROOT / CONFIG_PREFIX + "auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

SECRET_KEY = AUTH_TOKENS['SECRET_KEY']

AWS_ACCESS_KEY_ID = AUTH_TOKENS["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = AUTH_TOKENS["AWS_SECRET_ACCESS_KEY"]
AWS_STORAGE_BUCKET_NAME = 'edxuploads'

DATABASES = AUTH_TOKENS['DATABASES']

XQUEUE_INTERFACE = AUTH_TOKENS['XQUEUE_INTERFACE']

# Get the MODULESTORE from auth.json, but if it doesn't exist,
# use the one from common.py
MODULESTORE = AUTH_TOKENS.get('MODULESTORE', MODULESTORE)
CONTENTSTORE = AUTH_TOKENS.get('CONTENTSTORE', CONTENTSTORE)

OPEN_ENDED_GRADING_INTERFACE = AUTH_TOKENS.get('OPEN_ENDED_GRADING_INTERFACE', OPEN_ENDED_GRADING_INTERFACE)

PEARSON_TEST_USER = "pearsontest"
PEARSON_TEST_PASSWORD = AUTH_TOKENS.get("PEARSON_TEST_PASSWORD")

# Pearson hash for import/export
PEARSON = AUTH_TOKENS.get("PEARSON")

# Datadog for events!
DATADOG_API = AUTH_TOKENS.get("DATADOG_API")

# Analytics dashboard server
ANALYTICS_SERVER_URL = ENV_TOKENS.get("ANALYTICS_SERVER_URL")
ANALYTICS_API_KEY = AUTH_TOKENS.get("ANALYTICS_API_KEY", "")
