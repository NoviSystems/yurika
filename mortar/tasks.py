import datetime

from celery import shared_task
from django.db.transaction import atomic
from scrapy.crawler import CrawlerProcess
from django.conf import settings

import mortar.utils as utils
import mortar.models as models
import mortar.crawlers as crawler_classes

@shared_task(bind=True)
def analyze(self, analysis_pk):
    analysis = models.Analysis.objects.get(pk=analysis_pk)

    run_crawler(analysis.crawler.pk)
    preprocess(analysis.mindmap.pk)
    run_query(analysis.query.pk)
    
# Start Crawler
@shared_task(bind=True)
def run_crawler(self, crawler_pk):
    analysis = models.Analysis.objects.get(pk=0)
    crawler = models.Crawler.objects.get(pk=crawler_pk)
    elastic_url = settings.ES_URL

    crawler.clear_errors()

    if crawler.category != 'web':
        crawler.log_error('Only web crawlers are currently supported, not "{}"'.format(crawler.category))
        return

    name = crawler.name
    index = crawler.index.name
    seeds = [seed.urlseed.url for seed in crawler.seed_list.all()]

    crawler.process_id = self.request.id
    crawler.status = 0
    crawler.started_at = datetime.datetime.now()
    crawler.save()

    analysis.finished_at = None
    analysis.started_at = datetime.datetime.now()
    analysis.save()

    process = CrawlerProcess({
        'USER_AGENT': '',
        "SPIDER_MIDDLEWARES": {"mortar.crawlers.ErrorLogMiddleware": 1000},
    })
    try:
        process.crawl(crawler_classes.WebCrawler, start_urls=seeds, name=name, elastic_url=elastic_url, index=index, index_mapping=crawler._meta.index_mapping)
        process.start()
    except Exception as e:
        crawler.log_error(e)
        raise

    crawler.finished_at = datetime.datetime.now()
    crawler.status = 1
    crawler.process_id = None
    crawler.save()

# Sync Dictionaries
@shared_task(bind=True)
def sync_dictionaries(self):
    utils.update_dictionaries()

# Reindex and Tokenize Documents
@shared_task(bind=True)
def preprocess(self, tree_pk):
    analysis = models.Analysis.objects.get(pk=0)
    analysis.finished_at = None
    analysis.started_at = datetime.datetime.now()
    tree = models.Tree.objects.get(pk=tree_pk)
    tree.clear_errors()
    tree.started_at = datetime.datetime.now()
    tree.process_id = self.request.id
    tree.save()

    try:
        utils.process(tree, {'names': [], 'regexs': []}, analysis.query)
    except Exception as e:
        tree.log_error(e)
        raise

    tree.finished_at = datetime.datetime.now()
    tree.process_id = None
    tree.save()

# Run Query
@shared_task(bind=True)
def run_query(self, query_pk):
    analysis = models.Analysis.objects.get(pk=0)
    query = models.Query.objects.get(pk=query_pk)
    query.clear_errors()

    query.started_at = datetime.datetime.now()
    query.process_id = self.request.id
    query.save()


    try:
        utils.annotate(analysis)
    except Exception as e:
        query.log_error(e)
        raise

    query.finished_at = datetime.datetime.now()
    query.process_id = None
    query.save()

    analysis.finished_at = datetime.datetime.now()
    analysis.save()
