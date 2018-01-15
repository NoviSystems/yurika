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
    crawler = analysis.crawler
    elastic_url = settings.ES_URL

    if crawler.category == 'web':
        name = crawler.name
        index = crawler.index.name
        seeds = [seed.urlseed.url for seed in crawler.seed_list.all()]


        crawler.process_id = self.request.id
        crawler.status = 0
        crawler.started_at = datetime.datetime.now()
        crawler.save()

        analysis.started_at = datetime.datetime.now()
        analysis.status = 5
        analysis.save()

        process = CrawlerProcess({'USER_AGENT': ''})
        process.crawl(crawler_classes.WebCrawler, start_urls=seeds, name=name, elastic_url=elastic_url, index=index, index_mapping=crawler._meta.index_mapping)
        process.start()

        crawler.finished_at = datetime.datetime.now()
        crawler.status = 1
        crawler.process_id = None
        crawler.save()

    tree = analysis.mindmap
    tree.started_at = datetime.datetime.now()
    tree.process_id = self.request.id
    tree.save()

    analysis.status = 6
    analysis.save()

    utils.process(tree, {'names': [], 'regexs': []}, analysis.query)

    tree.finished_at = datetime.datetime.now()
    tree.process_id = None
    tree.save()

    query = analysis.query 
    query.started_at = datetime.datetime.now()
    query.process_id = self.request.id
    query.save()

    analysis.status = 7
    analysis.save()

    utils.annotate(analysis)

    query.finished_at = datetime.datetime.now()
    query.process_id = None
    query.save()

    analysis.status = 8
    analysis.finished_at = datetime.datetime.now()
    analysis.save()

    
# Start Crawler
@shared_task(bind=True)
def start_crawler(self, crawler_pk):
    analysis = models.Analysis.objects.get(pk=0)
    crawler = models.Crawler.objects.get(pk=crawler_pk)
    elastic_url = settings.ES_URL

    name = crawler.name
    index = crawler.index.name
    seeds = [seed.urlseed.url for seed in crawler.seed_list.all()]


    crawler.process_id = self.request.id
    crawler.status = 0
    crawler.started_at = datetime.datetime.now()
    crawler.save()

    analysis.started_at = datetime.datetime.now()
    analysis.status = 5
    analysis.save()

    process = CrawlerProcess({'USER_AGENT': ''})
    process.crawl(crawler_classes.WebCrawler, start_urls=seeds, name=name, elastic_url=elastic_url, index=index, index_mapping=crawler._meta.index_mapping)
    process.start()

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
    tree = models.Tree.objects.get(pk=tree_pk)
    tree.started_at = datetime.datetime.now()
    tree.process_id = self.request.id
    tree.save()

    analysis.status = 6
    analysis.save()

    utils.process(tree, {'names': [], 'regexs': []}, analysis.query)

    tree.finished_at = datetime.datetime.now()
    tree.process_id = None
    tree.save()

# Run Query
@shared_task(bind=True)
def run_query(self, query_pk):
    analysis = models.Analysis.objects.get(pk=0)
    query = models.Query.objects.get(pk=query_pk)
    query.started_at = datetime.datetime.now()
    query.process_id = self.request.id
    query.save()

    analysis.status = 7
    analysis.save()

    utils.annotate(analysis)

    query.finished_at = datetime.datetime.now()
    query.process_id = None
    query.save()

    analysis.status = 8
    analysis.finished_at = datetime.datetime.now()
    analysis.save()
