import scrapy
import time, datetime
import argparse, json
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
            self.errback(failure)
            raise e
    return catch_err


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
            #process_request="add_errback",
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

    #TODO: Commented out below is an attempt to log http errors and exceptions
    #      from scrapy. There's apparently no good way to do it when using a
    #      CrawlSpider. I think the only reasonable thing to do is write a
    #      middleware for logging.
    '''
    @log_errors_decorator
    def start_requests(self):
        """
        Overwrite scrapy.Spider.start_requests to add error callback to initial
        requests.
        """
        try:
            for request in super().start_requests():
                request.errback = self.errback
                yield request
        except Exception as e:
            self.errback(e)
            raise
    '''
    '''
    @log_errors_decorator
    def add_errback(self, request):
        """Add an error callback to the given request and return it."""
        request.errback = self.errback
        return request
    '''

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
        doc['tstamp'] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S.%f")
        doc['content'] = soup.get_text()
        doc['title'] = soup.title.string
        self.client.index(index=self.index_name, id=response.url, doc_type='doc', body=json.dumps(doc))         

        doc_item = Document(url=doc['url'], tstamp=doc['tstamp'], content=doc['content'], title=doc['title'])

        return doc_item

    def errback(self, failure):
        #TODO: If HTTP status code error returned, include that in log_error()
        analysis = models.Analysis.objects.get(pk=0)
        analysis.crawler.log_error(failure)
