"""
This config file runs the simplest dev environment using sqlite, and db-based
sessions. Assumes structure:

/envroot/
        /db   # This is where it'll write the database file
        /mitx # The location of this repo
        /log  # Where we're going to write log files
"""
from .common import *
from .logsettings import get_logger_config
import os
from path import path

INSTALLED_APPS = [
    app
    for app
    in INSTALLED_APPS
    if not app.startswith('askbot')
]

# Nose Test Runner
INSTALLED_APPS += ['django_nose']
NOSE_ARGS = ['--cover-erase', '--with-xunit', '--with-xcoverage', '--cover-html',
             '--cover-inclusive', '--cover-html-dir', os.environ.get('NOSE_COVER_HTML_DIR', 'cover_html')]
for app in os.listdir(PROJECT_ROOT / 'djangoapps'):
    NOSE_ARGS += ['--cover-package', app]
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Local Directories
TEST_ROOT = path("test_root")
# Want static files in the same dir for running on jenkins.
STATIC_ROOT = TEST_ROOT / "staticfiles" 

COURSES_ROOT = TEST_ROOT / "data"
DATA_DIR = COURSES_ROOT
MAKO_TEMPLATES['course'] = [DATA_DIR]
MAKO_TEMPLATES['sections'] = [DATA_DIR / 'sections']
MAKO_TEMPLATES['custom_tags'] = [DATA_DIR / 'custom_tags']
MAKO_TEMPLATES['main'] = [PROJECT_ROOT / 'templates', 
                          DATA_DIR / 'info',
                          DATA_DIR / 'problems']

LOGGING = get_logger_config(TEST_ROOT / "log", 
                            logging_env="dev",
                            tracking_filename="tracking.log",
                            debug=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': PROJECT_ROOT / "db" / "mitx.db",
    }
}

CACHES = {
    # This is the cache used for most things. Askbot will not work without a 
    # functioning cache -- it relies on caching to load its settings in places.
    # In staging/prod envs, the sessions also live here.
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mitx_loc_mem_cache',
        'KEY_FUNCTION': 'util.memcache.safe_key',
    },

    # The general cache is what you get if you use our util.cache. It's used for
    # things like caching the course.xml file for different A/B test groups.
    # We set it to be a DummyCache to force reloading of course.xml in dev.
    # In staging environments, we would grab VERSION from data uploaded by the
    # push process.
    'general': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'KEY_PREFIX': 'general',
        'VERSION': 4,
        'KEY_FUNCTION': 'util.memcache.safe_key',
    }
}

# Dummy secret key for dev
SECRET_KEY = '85920908f28904ed733fe576320db18cabd7b6cd'

############################ FILE UPLOADS (ASKBOT) #############################
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = TEST_ROOT / "uploads"
MEDIA_URL = "/static/uploads/"
STATICFILES_DIRS.append(("uploads", MEDIA_ROOT))

new_staticfiles_dirs = []
# Strip out any static files that aren't in the repository root
# so that the tests can run with only the mitx directory checked out
for static_dir in STATICFILES_DIRS:
    # Handle both tuples and non-tuple directory definitions
    try:
        _, data_dir = static_dir
    except ValueError:
        data_dir = static_dir

    if data_dir.startswith(REPO_ROOT):
        new_staticfiles_dirs.append(static_dir)
STATICFILES_DIRS = new_staticfiles_dirs

FILE_UPLOAD_TEMP_DIR = PROJECT_ROOT / "uploads"
FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
)
