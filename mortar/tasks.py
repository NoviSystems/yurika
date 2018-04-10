from multiprocessing import Process

import dramatiq
from scrapy.crawler import CrawlerProcess

from mortar import crawlers


def _crawl(task_id):
    process = CrawlerProcess()

    process.crawl(crawlers.WebCrawler, task_id=task_id)
    process.start()


@dramatiq.actor(max_retries=0)
def crawl(task_id):
    proc = Process(target=_crawl, args=(task_id, ))
    proc.start()
    proc.join()
