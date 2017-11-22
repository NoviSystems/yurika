import datetime

from celery import shared_task
from django.db.transaction import atomic
from scrapy.crawler import CrawlerProcess
from django.conf import settings

import mortar.utils as utils
import mortar.models as models
import mortar.crawlers as crawler_classes

# Start Crawler
@shared_task(bind=True)
def start_crawler(self, crawler_pk):
    crawler = models.Crawler.objects.get(pk=crawler_pk)
    elastic_url = settings.ES_URL

    if crawler.process_id:
        return crawler.process_id

    if crawler.category == 'web':
        name = crawler.name
        index = crawler.index.name
        seeds = [seed.urlseed.url for seed in crawler.seed_list.all()]

        crawler.process_id = self.request.id
        crawler.status = 'Running'
        crawler.started_at = datetime.datetime.now()
        crawler.save()

        process = CrawlerProcess({'USER_AGENT': ''})
        process.crawl(crawler_classes.WebCrawler, start_urls=seeds, name=name, elastic_url=elastic_url, index=index)
        process.start()

        crawler.finished_at = datetime.datetime.now()
        crawler.status = 'Finished'
        crawler.process_id = None
        crawler.save()

    else:
        print("file crawler requested")

# Sync Dictionaries
@shared_task(bind=True)
def sync_dictionaries(self):
    utils.update_dictionaries()

# Reindex and Tokenize Documents
@shared_task(bind=True)
def preprocess(self, tree_pk, query):
    tree = models.Tree.objects.get(pk=tree_pk)
    tree.status = 'r'
    tree.save()

    utils.process(tree, query)
    
    tree.status = 'f'
    tree.save()

# Run Query
@shared_task(bind=True)
def run_query(self, tree_pk, category, query_pk):
    tree = models.Tree.objects.get(pk=tree_pk)
    query = models.Query.objects.get(pk=query_pk)
    query.status = 'r'
    query.save()

    utils.annotate(tree, category, query)

    query.status = 'f'
    query.save()
