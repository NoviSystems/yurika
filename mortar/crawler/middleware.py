import logging

from scrapy.http import Request
from w3lib.url import safe_url_string


class LogExceptionMiddleware(object):

    def process_spider_exception(self, response, exception, spider):
        spider.task.log_exception(exception)


class BlockDomainMiddleware(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def filter_results(self, results, spider):
        for value in results:
            if isinstance(value, Request):
                if self.should_follow(value, spider):
                    yield value
                else:
                    self.logger.info(f"Ignoring URL on blocked list: {value.url}")
            else:
                yield value

    def should_follow(self, request, spider):
        escaped_url = safe_url_string(request.url, request.encoding)
        block_re = spider.task.crawler.block_re

        if block_re is not None:
            return bool(block_re.match(escaped_url))
        return True

    def process_start_requests(self, start_requests, spider):
        return self.filter_results(start_requests, spider)

    def process_spider_output(self, response, result, spider):
        return self.filter_results(result, spider)
