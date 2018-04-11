from scrapy.crawler import CrawlerProcess
from scrapy.utils import log

from .spiders import WebCrawler

__all__ = ['crawl']


def crawl(task):
    # prevent scrapy from mucking with our logging configuration
    log.dictConfig = lambda _: _
    process = CrawlerProcess(install_root_handler=False)

    process.crawl(WebCrawler, task=task)
    process.start()
