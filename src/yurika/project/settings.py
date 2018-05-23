'''
-*- Development Settings -*-

This file contains development-specific settings. You can run the django
development server without making any changes to this file, but it's not
suitable for production. The production settings files are located under
the './deploy' directory.
'''

from .common_settings import *  # noqa
from .common_settings import env, path


# Prevent accidental sending of emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


MEDIA_ROOT = path(env("MEDIA_ROOT"))
