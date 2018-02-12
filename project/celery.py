import os
from celery import Celery
import environ

envfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(envfile):
    environ.Env.read_env(envfile)

app = Celery("mortar")

app.config_from_object('django.conf:settings', namespace="CELERY")

app.autodiscover_tasks()
