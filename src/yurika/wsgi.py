"""
WSGI config

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os.path

from django.core.wsgi import get_wsgi_application
from environ import Env


envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(envfile):
    Env.read_env(envfile)

application = get_wsgi_application()
