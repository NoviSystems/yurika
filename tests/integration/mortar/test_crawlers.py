import time
from urllib.parse import urljoin

from django.test import LiveServerTestCase, override_settings
from django.urls import reverse
from django_dramatiq.test import DramatiqTestCase

from mortar import models


STATUS = models.Task.STATUS


@override_settings(ROOT_URLCONF='tests.integration.mortar.testapp.urls')
class CrawlerTests(DramatiqTestCase, LiveServerTestCase):

    def test_crawl(self):
        # create a crawler and it's management task
        url = urljoin(self.live_server_url, reverse('a'))
        crawler = models.Crawler.objects.create(start_urls=url)

        # start the task
        crawler.start()

        # wait for the task to complete
        self.broker.join(crawler.task.task.queue_name)
        self.worker.join()

        # the task should be done
        crawler.task.refresh_from_db()
        self.assertEqual(crawler.task.status, STATUS.done)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be three crawled documents
        self.assertEqual(crawler.documents.search().count(), 3)

    def test_stop(self):
        # create a crawler and it's management task
        url = urljoin(self.live_server_url, reverse('ref-slow'))
        crawler = models.Crawler.objects.create(start_urls=url)

        # send off the task and revoke task
        crawler.start()
        time.sleep(.5)  # 'slow' view takes .5 seconds
        crawler.task.refresh_from_db()
        crawler.stop()

        # wait for the task to complete
        self.broker.join(crawler.task.task.queue_name)
        self.worker.join()

        # the task should be aborted
        crawler.task.refresh_from_db()
        self.assertEqual(crawler.task.status, STATUS.aborted)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be less than three crawled documents
        self.assertGreater(crawler.documents.search().count(), 0)
        self.assertLess(crawler.documents.search().count(), 4)

    def test_resume(self):
        # Start and stop a crawler
        self.test_stop()

        # then resume the crawler
        crawler = models.Crawler.objects.get()
        crawler.resume()

        # wait for the task to complete
        self.broker.join(crawler.task.task.queue_name)
        self.worker.join()

        # the task should be done
        crawler.task.refresh_from_db()
        self.assertEqual(crawler.task.status, STATUS.done)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be four crawled documents
        self.assertEqual(crawler.documents.search().count(), 4)

    def test_restart(self):
        # Start and stop a crawler
        self.test_stop()

        # then restart the crawler
        crawler = models.Crawler.objects.get()
        crawler.restart()

        # wait for the task to complete
        self.broker.join(crawler.task.task.queue_name)
        self.worker.join()

        # the task should be done
        crawler.task.refresh_from_db()
        self.assertEqual(crawler.task.status, STATUS.done)

        # ensure the index has been populated
        crawler.index.refresh()

        # and there should be *more* than four crawled documents
        self.assertGreater(crawler.documents.search().count(), 4)
