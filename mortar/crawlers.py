# uncompyle6 version 2.12.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 2.7.13 (default, Jan 19 2017, 14:48:08) 
# [GCC 6.3.0 20170118]
# Embedded file name: /home/mejohn/itng/yurika/mortar/crawlers.py
# Compiled at: 2017-09-06 09:48:29
# Size of source mod 2**32: 1770 bytes
import scrapy
import time
import datetime
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from django.conf import settings
from elasticsearch.client import IndicesClient

class WebCrawler(scrapy.spiders.CrawlSpider):
    name = 'Test'
    start_urls = []
    client = settings.ES_CLIENT

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.start_urls = kwargs.get('urls')
        self.index_name = kwargs.get('index')
        self._compile_rules()
        index_mapping = kwargs.get('index_mapping')
        i_client = IndicesClient(self.client)
        if not i_client.exists(self.index_name):
            i_client.create(index=self.index_name, body=index_mapping)
            time.sleep(10)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        doc = {}
        doc['url'] = response.url
        doc['tstamp'] = datetime.datetime.strptime(datetime.now(), '%Y-%m-%dT%H%M%S.%f')
        doc['content'] = soup.get_text()
        doc['title'] = soup.title.string
        self.client.index(index=self.index_name, id=response.url, body=json.dumps(doc))


parser = ArugmentParser(description='Start a crawler')
parser.add_argument('type', choices=['web', 'txt'])
parser.add_argument('name')
parser.add_argument('-u', '--urls', nargs='+', required=True)
args = vars(parser.parse_args())
print(args)
if args['type'] == 'web':
    process = CrawlerProcess({'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36'})
    process.crawl(WebCrawler, name=args['name'], urls=args['urls'])
# okay decompiling crawlers.cpython-35.pyc
