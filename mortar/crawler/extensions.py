from scrapy import signals


class TaskRevoked(object):
    """
    Extension that forces spiders to close if the associated task
    is flagged in the revoke cache.
    """

    def __init__(self, crawler):
        self.crawler = crawler

        crawler.signals.connect(
            self.task_revoked,
            signal=signals.response_received
        )

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def task_revoked(self, response, request, spider):
        spider.task.refresh_from_db()

        if spider.task.revoked:
            self.crawler.engine.close_spider(spider, 'taskrevoked')
