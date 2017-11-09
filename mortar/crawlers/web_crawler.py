import scrapy
import time, datetime
import argparse, json
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.client import IndicesClient
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractor import LinkExtractor
from scrapy.spiders import Rule, CrawlSpider

class Document(scrapy.Item):
    refer_url = scrapy.Field()
    url = scrapy.Field()
    content = scrapy.Field()
    tstamp = scrapy.Field(serializer=str)
    title = scrapy.Field()


class WebCrawler(CrawlSpider):
    name = 'MyTest'
    rules = (
        Rule(LinkExtractor(canonicalize=True, unique=True), follow=True, callback="parse_item"),
    )
    client = Elasticsearch(['http://10.36.1.1:9200/'], connection_class=RequestsHttpConnection)

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name')
        self.index_name = kwargs.get('index')
        self.start_urls = kwargs.get('start_urls')
        self._compile_rules()

        index_mapping = kwargs.get('index_mapping')
        i_client = IndicesClient(self.client)
        if not i_client.exists(self.index_name):
            i_client.create(index=self.index_name, body=index_mapping)
            time.sleep(10)

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

parser = argparse.ArgumentParser(description="Start a crawler")
parser.add_argument('name')
parser.add_argument('index')
parser.add_argument('--urls', nargs='+')
args = vars(parser.parse_args())
process = CrawlerProcess({'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36'})
process.crawl(WebCrawler, start_urls=args['urls'], name=args['name'], index=args['index'])
process.start()
