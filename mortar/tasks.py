import datetime

from celery import task
from django.db.transaction import atomic

import mortar.utils as utils
import mortar.models as models

# Start Crawler
@task()
def start_crawler(crawler):
    pass

# Sync Dictionaries
@task()
def sync_dictionaries():
    utils.update_dictionaries()

# Reindex and Tokenize Documents
@task()
def preprocess(tree_pk, query):
    tree = models.Tree.objects.get(pk=tree_pk)
    utils.process(tree, query)

# Run Query
@task()
def run_query(tree_pk, category, query_pk):
    tree = models.Tree.objects.get(pk=tree.pk)
    query = models.Query.objects.get(pk=query.pk)
    utils.annotate(tree, category, query)
