#!/usr/bin/env python
import os
import sys
from argparse import ArgumentParser


DEV_CONF = """\
'''
-*- Development Settings -*-

This file contains development-specific settings. You can run the django
development server without making any changes to this file, but it's not
suitable for production.
'''
from yurika.settings import *  # noqa


# Prevent accidental sending of emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
"""


PROD_CONF = """\
'''
-*- Production Settings -*-

This file contains production-specific settings. Complete the deployment
checklist and make any necessary changes.

https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/
'''

from yurika.settings import *  # noqa


ADMINS = [
    # ('Admin Name', 'admin.email@example.com'),
]

# To force SSL if the upstream proxy server doesn't do it for us, set to True
SECURE_SSL_REDIRECT = False


# manifest storage is useful for its automatic cache busting properties
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
"""


DEV_ENV = """\
# Environment settings suitable for development.
# Note that these settings are *not* secure.

DEBUG=true
SECRET_KEY="not-so-secret"
ALLOWED_HOSTS="*"

DATABASE_URL="sqlite:///db.sqlite3"
DRAMATIQ_BROKER_URL="redis://"
ELASTICSEARCH_URL="http://localhost:9200/"

# Adds sentry error reporting. See yurika.settings for details.
# SENTRY_DSN=""
"""

PROD_ENV = """\
# Environment settings template.

DEBUG=false
SECRET_KEY=""
ALLOWED_HOSTS=""

DATABASE_URL=""
DRAMATIQ_BROKER_URL=""
ELASTICSEARCH_URL=""

# Adds sentry error reporting. See yurika.settings for details.
# SENTRY_DSN=""
"""


def init():
    parser = ArgumentParser(description='Initialize a new configuration directory.')
    parser.add_argument('directory', type=str)
    parser.add_argument('--dev', dest='dev', action='store_true', default=False,
                        help="Use settings more suitable for development.")

    options = parser.parse_args()

    directory = os.path.abspath(options.directory)
    settings = os.path.join(directory, 'settings.py')
    dotenv = os.path.join(directory, 'yurika.env')

    if not os.path.isdir(directory):
        parser.error(f"Directory '{directory}' does not exist.")
    if os.path.exists(settings):
        parser.error(f"A file already exists at '{settings}'.")
    if os.path.exists(dotenv):
        parser.error(f"A file already exists at '{dotenv}'.")

    with open(settings, 'w') as file:
        file.write(DEV_CONF if options.dev else PROD_CONF)
        print('Yurika settings created...')
    with open(dotenv, 'w') as file:
        file.write(DEV_ENV if options.dev else PROD_ENV)
        print('Yurika environment file created...')
    print('\nDone!')


def main():
    sys.path.insert(0, os.environ['YURIKA_CONF'])
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
