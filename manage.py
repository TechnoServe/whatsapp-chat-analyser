#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from django.contrib.auth import get_user_model

if __name__ == '__main__':

    if 'DJANGO_ADMIN_USERNAME' in os.environ:
        print ("Using the PRODUCTION settings")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.production")
        from analyser.settings.production import *
    else:
        print ("Using the DEVELOPMENT settings")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyser.settings.development")
        from analyser.settings.development import *

    try:
        import django
        django.setup()

        from django.core.management.commands.runserver import Command as runserver
        runserver.default_port = DEFAULT_PORT
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        raise

    User = get_user_model()
    execute_from_command_line(sys.argv)
