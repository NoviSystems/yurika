import os

from django.conf import settings


def path(value):
    """
    Builds absolute paths relative to settings.BASE_DIR.
    """
    return os.path.abspath(os.path.join(settings.BASE_DIR, value))
