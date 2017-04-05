import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from .common_settings import *

# Copy this file to settings.py to deploy this app.

# This file contains deployment-specific settings. It can also override any
# settings in common_settings.py
# You should leave settings.py out of source control (but still back
# it up somehow in production)

# You can run the django test server without adding anything to this file,
# but it's unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# Before deploying to production, uncomment and configure at least the
# following:

# Set this to False to turn off debug tracebacks to the browser on unhandled
# exceptions
#DEBUG = False

# With DEBUG off, Django checks that the Host header in requests matches one of
# these. If you turn off DEBUG and you're suddenly getting HTTP 400 Bad
# Request responses, you need to add the host names to this list
#ALLOWED_HOSTS = []

# Set your production database parameters here! See
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
#DATABASE=...

# When DEBUG is off, these email addresses will receive an email for any
# unhandled exceptions while processing a request. See the logging
# configuration in common_settings for how that is set up.
ADMINS = [
    #('Admin Name', 'adminemail@example.com'),
]

# Django's test server serves static files for you, but in production,
# Django expects your web server to take care of that. You will need to set
# STATIC_ROOT to a directory on your filesystem, and STATIC_URL to something
# like "/static/". Then configure your webserver to serve that directory at
# that url.
# Finally, run "manage.py collectstatic" and django will copy static files
# from various places into your STATIC_ROOT. You need to re-run collectstatic
# each time you redeploy with changes to static files.
#STATIC_ROOT = os.path.join(BASE_DIR, "static_root")
#STATIC_URL = "/static/"

from elasticsearch import Elasticsearch, RequestsHttpConnection
ES_CLIENT = Elasticsearch(
    ['http://127.0.0.1:9200/'],
    connection_class=RequestsHttpConnection
)

DICTIONARIES_PATH = 'path/to/dictionaries'
