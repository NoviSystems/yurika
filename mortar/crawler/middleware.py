import functools
import logging
import re

from scrapy.http import Request
from scrapy.utils.httpobj import urlparse_cached


logger = logging.getLogger(__name__)


class LogExceptionMiddleware(object):

    def process_spider_exception(self, response, exception, spider):
        spider.task.log_exception(exception)


class BlockedDomainMiddleware(object):
    """
    Similar to OffsiteMiddleware, but blocks instead of allows domains.

    The spider should accept a list of `blocked_domains`.
    """

    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.stats)

    def process_spider_output(self, response, result, spider):
        for item in result:
            if isinstance(item, Request) and self.should_block(item, spider):
                self.stats.inc_value('block/filtered', spider=spider)
            else:
                yield item

    def should_block(self, request, spider):
        block_re = self.get_host_regex(spider)
        if block_re is None or request.dont_filter:
            return False

        host = urlparse_cached(request).hostname or ''
        return bool(block_re.search(host))

    @functools.lru_cache()
    def get_host_regex(self, spider):
        blocked_domains = getattr(spider, 'blocked_domains', None)
        if not blocked_domains:
            return None

        for domain in blocked_domains:
            assert domain, "blocked_domains only accepts domains, not empty values."
            assert '://' not in domain, "blocked_domains only accepts domains, not URLs."

        return re.compile(r'^(.*)(%s)' % '|'.join(re.escape(d) for d in blocked_domains))
