

import os

from django.core.wsgi import get_wsgi_application

from analyser.settings.base import *

if 'DJANGO_ADMIN_USERNAME' in os.environ:
    print ("Using the PRODUCTION settings")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.production")
    from analyser.settings.production import *
    from analyser.settings.development import *
else:
    print ("Using the DEVELOPMENT settings")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.development")
    from analyser.settings.development import *

application = get_wsgi_application()