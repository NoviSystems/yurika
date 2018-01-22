import scrapy
import time
from datetime import datetime
import argparse, json
from django.utils import timezone
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.client import IndicesClient
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule, CrawlSpider

from mortar import models

def log_errors_decorator(func):
    def catch_err(self, *args, **kwargs):
        try:
            ret = func(self, *args, **kwargs)
            return ret
        except Exception as e:
            analysis = models.Analysis.objects.get(pk=0)
            analysis.crawler.log_error(e)
            raise e
    return catch_err

class ErrorLogMiddleware(object):

    def process_spider_exception(self, response, exception, spider):
        analysis = models.Analysis.objects.get(pk=0)
        analysis.crawler.log_error("{} {}".format(exception, response))

class Document(scrapy.Item):
    refer_url = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    tstamp = scrapy.Field(serializer=str)
    title = scrapy.Field()


class WebCrawler(CrawlSpider):
    name = 'MyTest'
    rules = (
        Rule(
            LinkExtractor(canonicalize=True, unique=True),
            follow=True,
            callback="parse_item",
        ),
    )

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.index_name = kwargs.get('index')
        self.start_urls = kwargs.get('start_urls')
        self.client = Elasticsearch([kwargs.get('elastic_url')], connection_class=RequestsHttpConnection)
        self._compile_rules()

        index_mapping = kwargs.get('index_mapping')
        i_client = IndicesClient(self.client)
        if not i_client.exists(self.index_name):
            i_client.create(index=self.index_name)
            time.sleep(10)

    @log_errors_decorator
    def start_requests(self):
        """Overwrite scrapy.Spider.start_requests to log errors."""
        # Yes, we both use log_errors_decorator and have a try..except here,
        # because this is a generator, errors in super().start_requests() may
        # not be caught otherwise.
        try:
            for request in super().start_requests():
                yield request
        except Exception as e:
            analysis = models.Analysis.objects.get(pk=0)
            analysis.crawler.log_error(e)
            raise

    @log_errors_decorator
    def parse_item(self, response):
        #reformat any html entities that make tags appear in text
        text = response.text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        soup = BeautifulSoup(response.text, 'lxml')

        for script in soup(["script", "style"]):
            script.decompose()

        doc = {}
        doc['url'] = response.url
        doc['refer_url'] = str(response.request.headers.get('Referer', None))
        doc['tstamp'] = datetime.strftime(timezone.now(), "%Y-%m-%dT%H:%M:%S.%f")
        doc['content'] = soup.get_text()
        doc['title'] = soup.title.string
        self.client.index(index=self.index_name, id=response.url, doc_type='doc', body=json.dumps(doc))         

        doc_item = Document(url=doc['url'], tstamp=doc['tstamp'], content=doc['content'], title=doc['title'])

        return doc_item
