"""
This config file runs the simplest dev environment using sqlite, and db-based
sessions. Assumes structure:

/envroot/
        /db   # This is where it'll write the database file
        /mitx # The location of this repo
        /log  # Where we're going to write log files
"""
from common import *

STATIC_GRAB = True

LOGGING = logsettings.get_logger_config(ENV_ROOT / "log", 
                                        logging_env="dev",
                                        tracking_filename="tracking.log",
                                        debug=False)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ENV_ROOT / "db" / "mitx.db",
    }
}

CACHES = {
    # This is the cache used for most things. Askbot will not work without a 
    # functioning cache -- it relies on caching to load its settings in places.
    # In staging/prod envs, the sessions also live here.
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mitx_loc_mem_cache'
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
    }
}

# Dummy secret key for dev
SECRET_KEY = '85920908f28904ed733fe576320db18cabd7b6cd'

############################ FILE UPLOADS (ASKBOT) #############################
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = ENV_ROOT / "uploads"
MEDIA_URL = "/discussion/upfiles/"
FILE_UPLOAD_TEMP_DIR = ENV_ROOT / "uploads"
FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
)
