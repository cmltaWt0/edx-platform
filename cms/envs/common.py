"""
This is the common settings file, intended to set sane defaults. If you have a
piece of configuration that's dependent on a set of feature flags being set,
then create a function that returns the calculated value based on the value of
MITX_FEATURES[...]. Modules that extend this one can change the feature
configuration in an environment specific config file and re-calculate those
values.

We should make a method that calls all these config methods so that you just
make one call at the end of your site-specific dev file to reset all the
dependent variables (like INSTALLED_APPS) for you.

Longer TODO:
1. Right now our treatment of static content in general and in particular
   course-specific static content is haphazard.
2. We should have a more disciplined approach to feature flagging, even if it
   just means that we stick them in a dict called MITX_FEATURES.
3. We need to handle configuration for multiple courses. This could be as
   multiple sites, but we do need a way to map their data assets.
"""

import sys
import tempfile
from path import path

############################ FEATURE CONFIGURATION #############################

MITX_FEATURES = {
    'USE_DJANGO_PIPELINE': True,
}

############################# SET PATH INFORMATION #############################
PROJECT_ROOT = path(__file__).abspath().dirname().dirname()  # /mitx/cms
COMMON_ROOT = PROJECT_ROOT.dirname() / "common"
ENV_ROOT = PROJECT_ROOT.dirname().dirname()  # virtualenv dir /mitx is in
COURSES_ROOT = ENV_ROOT / "data"

# FIXME: To support multiple courses, we should walk the courses dir at startup
DATA_DIR = COURSES_ROOT

sys.path.append(ENV_ROOT)
sys.path.append(PROJECT_ROOT / 'djangoapps')
sys.path.append(PROJECT_ROOT / 'lib')
sys.path.append(COMMON_ROOT / 'djangoapps')
sys.path.append(COMMON_ROOT / 'lib')


############################# WEB CONFIGURATION #############################
# This is where we stick our compiled template files.
MAKO_MODULE_DIR = tempfile.mkdtemp('mako')
MAKO_TEMPLATES = {}
MAKO_TEMPLATES['main'] = [
    PROJECT_ROOT / 'templates',
    COMMON_ROOT / 'djangoapps' / 'pipeline_mako' / 'templates'
]

MITX_ROOT_URL = ''

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.auth',  # this is required for admin
    'django.core.context_processors.csrf',  # necessary for csrf protection
)

################################# Middleware ###################################
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'staticfiles.finders.FileSystemFinder',
    'staticfiles.finders.AppDirectoriesFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # Instead of AuthenticationMiddleware, we use a cached backed version
    'cache_toolbox.middleware.CacheBackedAuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'track.middleware.TrackMiddleware',
    'mitxmako.middleware.MakoMiddleware',

    'django.middleware.transaction.TransactionMiddleware',
)

############################ SIGNAL HANDLERS ################################
import monitoring.exceptions  # noqa

############################ DJANGO_BUILTINS ################################
# Change DEBUG/TEMPLATE_DEBUG in your environment settings files, not here
DEBUG = False
TEMPLATE_DEBUG = False

# Site info
SITE_ID = 1
SITE_NAME = "localhost:8000"
HTTPS = 'on'
ROOT_URLCONF = 'mitx.cms.urls'
IGNORABLE_404_ENDS = ('favicon.ico')

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'registration@mitx.mit.edu'
DEFAULT_FEEDBACK_EMAIL = 'feedback@mitx.mit.edu'
ADMINS = (
    ('MITx Admins', 'admin@mitx.mit.edu'),
)
MANAGERS = ADMINS

# Static content
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATIC_ROOT = ENV_ROOT / "staticfiles" 

# FIXME: We should iterate through the courses we have, adding the static 
#        contents for each of them. (Right now we just use symlinks.)
STATICFILES_DIRS = [
    PROJECT_ROOT / "static",

# This is how you would use the textbook images locally
#    ("book", ENV_ROOT / "book_images")
]

# Locale/Internationalization
TIME_ZONE = 'America/New_York'  # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
LANGUAGE_CODE = 'en'            # http://www.i18nguy.com/unicode/language-identifiers.html
USE_I18N = True
USE_L10N = True

# Messages
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

############################### Pipeline #######################################

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_CSS = {
    'base-style': {
        'source_filenames': ['sass/base-style.scss'],
        'output_filename': 'css/base-style.css',
    },
}

PIPELINE_ALWAYS_RECOMPILE = ['sass/base-style.scss']

PIPELINE_JS = {
}

PIPELINE_COMPILERS = [
    'pipeline.compilers.sass.SASSCompiler',
    'pipeline.compilers.coffee.CoffeeScriptCompiler',
]

PIPELINE_SASS_ARGUMENTS = '-t compressed -r {proj_dir}/static/sass/bourbon/lib/bourbon.rb'.format(proj_dir=PROJECT_ROOT)

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.yui.YUICompressor'

STATICFILES_IGNORE_PATTERNS = (
    "sass/*",
    "coffee/*",
    "*.py",
    "*.pyc"
)

PIPELINE_YUI_BINARY = 'yui-compressor'
PIPELINE_SASS_BINARY = 'sass'
PIPELINE_COFFEE_SCRIPT_BINARY = 'coffee'

# Setting that will only affect the MITx version of django-pipeline until our changes are merged upstream
PIPELINE_COMPILE_INPLACE = True

############################ APPS #####################################

INSTALLED_APPS = (
    # Standard apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',

    # For CMS
    'contentstore',

    # For asset pipelining
    'pipeline',
    'staticfiles',
)
