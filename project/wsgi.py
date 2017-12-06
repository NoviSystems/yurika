"""
WSGI config

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

import environ

environ.Env.read_env(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
)

application = get_wsgi_application()
