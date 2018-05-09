from functools import wraps
from unittest import TestCase

from scrapy.http import Request
from scrapy.utils.test import get_crawler

from mortar.crawler.middleware import BlockedDomainMiddleware


def spider_middleware(**kwargs):
    """
    Create a spider and middleware and inject them into the test arguments.
    """
    kwargs.setdefault('name', 'spider')
    crawler = get_crawler()
    spider = crawler._create_spider(**kwargs)
    middleware = BlockedDomainMiddleware.from_crawler(crawler)

    def wrapper(test_method):
        @wraps(test_method)
        def wrapped(self):
            return test_method(self, spider=spider, middleware=middleware)
        return wrapped
    return wrapper


class BlockedDomainMiddlewareTestCase(TestCase):

    @spider_middleware(blocked_domains=['domain.org'])
    def test_should_block_obeys_dont_filter(self, spider, middleware):
        test_cases = [
            (Request('http://domain.org/1', dont_filter=True), False),
            (Request('http://domain.org/2'), True),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware(blocked_domains=['sub.domain.org', 'block.domain.org'])
    def test_block_subdomain_list(self, spider, middleware):
        test_cases = [
            (Request('http://sub.domain.org/1'), True),
            (Request('http://block.domain.org/2'), True),
            (Request('http://notblocked.domain.org/3'), False),
            (Request('http://nested.sub.domain.org/4'), True),
            (Request('http://domain.org/5'), False),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware(blocked_domains=['.domain.org'])
    def test_block_all_subdomains(self, spider, middleware):
        test_cases = [
            (Request('http://sub.domain.org/1'), True),
            (Request('http://another.domain.org/2'), True),
            (Request('http://nested.sub.domain.org/3'), True),
            (Request('http://domain.org/4'), False),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware(blocked_domains=['domain.org'])
    def test_block_entire_domain(self, spider, middleware):
        test_cases = [
            (Request('http://sub.domain.org/1'), True),
            (Request('http://another.domain.org/2'), True),
            (Request('http://nested.sub.domain.org/3'), True),
            (Request('http://domain.org/4'), True),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware()
    def test_no_blocked_domains(self, spider, middleware):
        test_cases = [
            (Request('http://domain.org/1'), False),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware(blocked_domains=[])
    def test_empy_blocked_domains(self, spider, middleware):
        test_cases = [
            (Request('http://domain.org/1'), False),
        ]

        for request, should_block in test_cases:
            with self.subTest(request=request, should_block=should_block):
                self.assertEqual(middleware.should_block(request, spider), should_block)

    @spider_middleware(blocked_domains=['https://domain.org'])
    def test_url_in_blocked_domains(self, middleware, spider):
        with self.assertRaises(AssertionError) as exc_info:
            middleware.get_host_regex(spider)

        msg = "blocked_domains only accepts domains, not URLs."
        self.assertEqual(str(exc_info.exception), msg)

    @spider_middleware(blocked_domains=[None])
    def test_empty_value_in_blocked_domains(self, middleware, spider):
        with self.assertRaises(AssertionError) as exc_info:
            middleware.get_host_regex(spider)

        msg = "blocked_domains only accepts domains, not empty values."
        self.assertEqual(str(exc_info.exception), msg)
