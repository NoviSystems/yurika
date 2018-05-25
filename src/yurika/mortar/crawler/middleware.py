import functools
import logging
import re

from scrapy.http import Request
from scrapy.utils.httpobj import urlparse_cached


logger = logging.getLogger(__name__)


class LogExceptionMiddleware(object):

    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.stats)

    def process_spider_exception(self, response, exception, spider):
        logger = getattr(spider, 'exception_logger', None)
        if logger is not None:
            logger(exception)
            self.stats.inc_value('exceptions/logged', spider=spider)


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

            # domains should not contain a scheme (//) or a path (/)
            assert '/' not in domain, "blocked_domains only accepts domains, not URLs."

        return re.compile(r'^(.*)(%s)' % '|'.join(re.escape(d) for d in blocked_domains))


class DistanceMiddleware(object):
    """
    Similar to DepthMiddleware, but the distance/depth only increases
    when traversing to a different domain.
    """

    def __init__(self, stats, maxdist, verbose):
        self.stats = stats
        self.maxdist = maxdist
        self.verbose = verbose

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        distance = settings.getint('DISTANCE_LIMIT')
        verbose = settings.getbool('DISTANCE_STATS_VERBOSE')
        return cls(crawler.stats, distance, verbose)

    def process_spider_output(self, response, result, spider):
        for item in result:
            if not isinstance(item, Request):
                yield item
                continue

            # only increase with domain change
            distance = response.meta.get('distance', 0)
            if self.different_domains(response, item):
                distance += 1

            if self.maxdist and distance > self.maxdist:
                logger.debug(
                    f"Ignoring link (distance > {self.maxdist}): {item}",
                    extra={'spider': spider}
                )
            else:
                if self.verbose:
                    self.stats.inc_value(f'request_distance_count/{distance}', spider=spider)
                self.stats.max_value('request_distance_max', distance, spider=spider)
                item.meta['distance'] = distance

                yield item

    def different_domains(self, response, request):
        a = urlparse_cached(response).hostname or ''
        b = urlparse_cached(request).hostname or ''
        return a != b
