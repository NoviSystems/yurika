import os

from celery import Celery
from environ import Env


envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(envfile):
    Env.read_env(envfile)

app = Celery('yurika')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
