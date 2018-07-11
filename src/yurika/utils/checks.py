import logging

from django.core.checks import Error, register
from django.db import connections
from django.db.utils import OperationalError
from elasticsearch import Elasticsearch

from . import log_level


@register()
def check_service_connections(app_configs, **kwargs):
    errors = []

    # databases
    for alias in connections:
        try:
            connections[alias].cursor()
        except OperationalError:
            errors.append(Error(f'No connection to database ({alias})', id='utils.E001'))

    # elasticsearch unnecessarily logs connection failures
    with log_level(logging.getLogger('elasticsearch'), logging.ERROR):
        if not Elasticsearch().ping():
            errors.append(Error('No connection to Elasticsearch', id='utils.E002'))

    return errors
