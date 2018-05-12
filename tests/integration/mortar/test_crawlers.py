import time
from urllib.parse import urljoin

from django.test import LiveServerTestCase, override_settings
from django_dramatiq.test import DramatiqTestCase

from mortar import models


STATUS = models.Task.STATUS


@override_settings(ROOT_URLCONF='tests.integration.mortar.testapp.urls')
class CrawlerTests(DramatiqTestCase, LiveServerTestCase):

    def test_simple(self):
        base_url = self.live_server_url

        # create a crawler and it's management task
        crawler = models.Crawler.objects.create(start_urls=urljoin(base_url, 'a'))
        task = crawler.task

        # send off the task
        task.send()

        # wait for the task to complete
        self.broker.join(task.task.queue_name)
        self.worker.join()

        # the task should be done
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.done)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be three crawled documents
        self.assertEqual(crawler.documents.search().count(), 3)

    def test_revoke(self):
        base_url = self.live_server_url

        # create a crawler and it's management task
        crawler = models.Crawler.objects.create(start_urls=urljoin(base_url, 'a'))
        task = crawler.task

        # send off the task and immediately revoke task
        task.send()
        task.revoke()

        # wait for the task to complete
        self.broker.join(task.task.queue_name)
        self.worker.join()

        # the task should be aborted
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.aborted)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be less than three crawled documents
        self.assertLess(crawler.documents.search().count(), 3)

    def test_resume(self):
        # Start and revoke a crawler
        self.test_revoke()

        # then resume the crawler
        crawler = models.Crawler.objects.get()
        crawler.restart()
        task = crawler.task

        # send off the task
        task.send()

        # wait for the task to complete
        self.broker.join(task.task.queue_name)
        self.worker.join()

        # the task should be done
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.done)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be three crawled documents
        self.assertEqual(crawler.documents.search().count(), 3)


class OpenCrawlerTests(DramatiqTestCase):
    # Test against the open internet

    def crawl(self, crawler):
        crawler.task.send()

        # wait a bit and revoke task
        time.sleep(2)
        crawler.task.revoke()
        crawler.task.refresh_from_db()

        # wait for the task to complete
        self.broker.join(crawler.task.task.queue_name)
        self.worker.join()

        crawler.task.refresh_from_db()
        crawler.index.refresh()

    def test_restart(self):
        # create a crawler and send off the task
        crawler = models.Crawler.objects.create(start_urls='https://www.ncsu.edu')

        # crawl for a bit
        self.crawl(crawler)

        # the task should be aborted and there should be some crawled documents
        initial_count = crawler.documents.search().count()
        self.assertEqual(crawler.task.status, STATUS.aborted)
        self.assertGreater(initial_count, 0)

        # then restart the task
        crawler.restart()

        # crawl for a bit
        self.crawl(crawler)

        # the task should be aborted and there should be more crawled documents
        doc_count = crawler.documents.search().count()
        self.assertEqual(crawler.task.status, STATUS.aborted)
        self.assertGreater(doc_count, initial_count)

        # there should be duplicate URLs (doc count != url count)
        url_count = len({hit.url for hit in crawler.documents.scan()})
        self.assertGreater(doc_count, url_count)

    def test_resume(self):
        # create a crawler and send off the task
        crawler = models.Crawler.objects.create(start_urls='https://www.ncsu.edu')

        # crawl for a bit
        self.crawl(crawler)

        # the task should be aborted and there should be some crawled documents
        initial_count = crawler.documents.search().count()
        self.assertEqual(crawler.task.status, STATUS.aborted)
        self.assertGreater(initial_count, 0)

        # then resume the task
        crawler.resume()

        # crawl for a bit
        self.crawl(crawler)

        # the task should be aborted and there should be more crawled documents
        doc_count = crawler.documents.search().count()
        self.assertEqual(crawler.task.status, STATUS.aborted)
        self.assertGreater(doc_count, initial_count)

        # there should not be duplicate URLs (doc count == url count)
        url_count = len({hit.url for hit in crawler.documents.scan()})
        self.assertEqual(doc_count, url_count)
