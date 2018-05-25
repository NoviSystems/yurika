from datetime import datetime

from bs4 import BeautifulSoup
from django.utils import timezone
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from .. import documents


class WebCrawler(CrawlSpider):
    name = 'crawler'

    rules = (
        Rule(
            LinkExtractor(canonicalize=True, unique=True),
            follow=True,
            callback='parse_item',
        ),
    )

    custom_settings = {
        'USER_AGENT': '',
        'ROBOTSTXT_OBEY': True,
        'SPIDER_MIDDLEWARES_BASE': {
            # default scrapy middleware
            'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': 50,
            'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 500,
            'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
            'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': 800,
            'scrapy.spidermiddlewares.depth.DepthMiddleware': 900,

            # default mortar middleware
            'yurika.mortar.crawler.middleware.LogExceptionMiddleware': 100,
            'yurika.mortar.crawler.middleware.BlockedDomainMiddleware': 500,
            'yurika.mortar.crawler.middleware.DistanceMiddleware': 900,
        },
    }

    def __init__(self, *args, task, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task

    def parse_item(self, response):
        crawler = self.task.crawler
        tokenizer = getattr(crawler, 'sentencetokenizer', None)

        soup = BeautifulSoup(response.text, 'lxml')

        for element in soup(['script', 'style']):
            element.decompose()

        text = soup.get_text()
        text = [line.strip() for line in text.splitlines()]
        text = [line for line in text if line]
        text = '\n'.join(text)

        doc = documents.Document(
            url=response.url,
            referer=str(response.request.headers.get('Referer', None)),
            title=soup.title.string if soup.title else "",
            html=response.text,
            text=text,
            timestamp=datetime.strftime(timezone.now(), "%Y-%m-%dT%H:%M:%S.%f"),
        )

        # save doc to crawler's document index
        crawler.documents.create(doc)

        # parse sentences from document
        if tokenizer is not None:
            tokenizer.tokenize(doc)
