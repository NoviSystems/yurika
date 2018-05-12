from functools import partial, wraps
from unittest import TestCase

from scrapy.http import Request, Response
from scrapy.utils.test import get_crawler

from mortar.crawler import middleware


def spider_middleware(middleware_cls, settings=None, **spider_kwargs):
    """
    Create a spider and middleware and inject them into the test arguments.
    """
    spider_kwargs.setdefault('name', 'spider')
    crawler = get_crawler(settings_dict=settings)
    spider = crawler._create_spider(**spider_kwargs)
    middleware = middleware_cls.from_crawler(crawler)

    def wrapper(test_method):
        @wraps(test_method)
        def wrapped(self):
            return test_method(self, spider=spider, middleware=middleware)
        return wrapped
    return wrapper


class BlockedDomainMiddlewareTestCase(TestCase):
    spider_middleware = partial(spider_middleware, middleware.BlockedDomainMiddleware)

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
    def test_scheme_in_blocked_domains(self, spider, middleware):
        with self.assertRaises(AssertionError) as exc_info:
            middleware.get_host_regex(spider)

        msg = "blocked_domains only accepts domains, not URLs."
        self.assertEqual(str(exc_info.exception), msg)

    @spider_middleware(blocked_domains=['domain.org/path'])
    def test_path_in_blocked_domains(self, spider, middleware):
        with self.assertRaises(AssertionError) as exc_info:
            middleware.get_host_regex(spider)

        msg = "blocked_domains only accepts domains, not URLs."
        self.assertEqual(str(exc_info.exception), msg)

    @spider_middleware(blocked_domains=[None])
    def test_empty_value_in_blocked_domains(self, spider, middleware):
        with self.assertRaises(AssertionError) as exc_info:
            middleware.get_host_regex(spider)

        msg = "blocked_domains only accepts domains, not empty values."
        self.assertEqual(str(exc_info.exception), msg)


class DistanceMiddlewareTestCase(TestCase):
    spider_middleware = partial(spider_middleware, middleware.DistanceMiddleware)

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_different_domains(self, spider, middleware):
        response, request = Response('http://domain.org'), Request('http://domain.org')
        self.assertFalse(middleware.different_domains(response, request))

        response, request = Response('http://domain.org'), Request('http://sub.domain.org')
        self.assertTrue(middleware.different_domains(response, request))

        response, request = Response('http://domain.org'), Request('http://domain.com')
        self.assertTrue(middleware.different_domains(response, request))

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_process_same_domain(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.org')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 0)

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_process_different_domain(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.com')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 1)

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_process_subdomain(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [Request('http://sub.domain.org')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 1)

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_process_middle_distance(self, spider, middleware):
        request = Request('http://domain.org', meta={'distance': 3})
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.com')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 4)

    @spider_middleware(settings={'DISTANCE_LIMIT': 5})
    def test_process_max_distance(self, spider, middleware):
        request = Request('http://domain.org', meta={'distance': 5})
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.com')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, [])

    @spider_middleware(settings={'DISTANCE_LIMIT': 0})
    def test_disabled(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.com')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 1)

    @spider_middleware(settings={'DISTANCE_STATS_VERBOSE': True})
    def test_stats(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [Request('http://domain.org'), Request('http://domain.com')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[0].meta['distance'], 0)
        self.assertEqual(out[1].meta['distance'], 1)

        stats = spider.crawler.stats
        self.assertEqual(stats.get_value('request_distance_count/0', spider=spider), 1)
        self.assertEqual(stats.get_value('request_distance_count/1', spider=spider), 1)
        self.assertEqual(stats.get_value('request_distance_max', spider=spider), 1)

    @spider_middleware(settings={'DISTNACE_LIMIT': 5})
    def test_non_request_ignored(self, spider, middleware):
        request = Request('http://domain.org')
        response = Response('http://domain.org', request=request)
        result = [None, Request('http://domain.org')]

        out = list(middleware.process_spider_output(response, result, spider))
        self.assertEqual(out, result)
        self.assertEqual(out[1].meta['distance'], 0)
