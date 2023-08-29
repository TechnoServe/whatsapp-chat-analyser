import os

# import base settings
from .base import *

ALLOWED_HOSTS = ['*']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
ENV_ROLE = 'prod'

if USE_S3 == 'False':
    # we are using the local file system to serve static files, so set the paths appropriately
    # STATIC_ROOT = '/opt/tafiti/static/'
    STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

STATICFILES_DIRS = [
    # '/opt/tafiti/analyser/static/'
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
]

STATIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
ADMIN_EMAILS = ['nniyomahoro@tns.org', 'smbonyumuhire@tns.org']

# The default port to serve the application from
DEFAULT_PORT = 9037