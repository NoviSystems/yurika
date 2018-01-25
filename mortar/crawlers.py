import time
import os
from datetime import datetime
import argparse, json
import re

import logging
log = logging.getLogger(__name__)

from django.utils import timezone
from django.conf import settings

from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.client import IndicesClient
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule, CrawlSpider
from scrapy.http import Request
from scrapy.exceptions import NotConfigured
from scrapy.utils.httpobj import urlparse_cached
from w3lib.url import safe_url_string

from mortar import models

def remove_prefix(s, prefix):
    return s[len(prefix):] if s.startswith(prefix) else s
def remove_suffix(s, suffix):
    return s[:-len(suffix)] if s.endswith(suffix) else s

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

class BlockUrlMiddleware(object):

    def __init__(self):

        # Read urls and build regex
        self.regex = self.build_regex(self.read_block_files())

        if not self.regex:
            raise NotConfigured  # Remove this middleware from the stack

    def read_block_files(self):
        """Yield every line from every file in BLOCK_LISTS setting."""
        for path in settings.BLOCK_LISTS:
            if not os.path.exists(path):
                raise ValueError("Misconfigured BLOCK_LISTS: File not found: "
                        "{}".format(path))
            with open(path) as f:
                yield from f

    def build_regex(self, urls):
        is_url = lambda url: len(url.strip()) > 0 and url[0] != '#'
        urls = filter(is_url, urls)
        re_part = '|'.join(re.escape(self.normalize_url(url)) for url in urls)
        if not re_part:
            return None
        regex = '^({})'.format(re_part)
        return re.compile(regex)

    def normalize_url(self, url):
        url = url.strip()
        url = remove_prefix(url, 'http://')
        url = remove_prefix(url, 'https://')
        url = remove_prefix(url, 'www.')
        url = remove_suffix(url, '/')
        return url

    def filter_results(self, results):
        for x in results:
            if isinstance(x, Request):
                if self.should_follow(x):
                    yield x
                else:
                    log.info("Ignoring URL on blocked list: {}".format(x.url))
            else:
                yield x

    def should_follow(self, request):
        escaped_url = safe_url_string(request.url, request.encoding)
        if self.regex.match(self.normalize_url(escaped_url)):
            return False

        return True

    def process_start_requests(self, start_requests, spider):
        return self.filter_results(start_requests)

    def process_spider_output(self, response, result, spider):
        return self.filter_results(result)


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
        doc['title'] = soup.title.string if soup.title else ""
        self.client.index(index=self.index_name, id=response.url, doc_type='doc', body=json.dumps(doc))         

        doc_item = Document(url=doc['url'], tstamp=doc['tstamp'], content=doc['content'], title=doc['title'])

        return doc_item
