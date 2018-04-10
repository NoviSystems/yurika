import logging
from contextlib import contextmanager
from urllib.parse import urljoin

from django.test import LiveServerTestCase, override_settings
from elasticsearch_dsl import Index
from project.utils.test import DramatiqTestCase
from mortar.models import Task

from mortar import models


STATUS = Task.STATUS


@contextmanager
def disable_logging(name):
    logger = logging.getLogger(name)
    level = logger.level
    logger.setLevel(logging.CRITICAL)
    yield
    logger.setLevel(level)


@override_settings(ROOT_URLCONF='tests.integration.mortar.testapp.urls')
class CrawlerTests(DramatiqTestCase, LiveServerTestCase):

    def test_simple(self):
        base_url = self.live_server_url

        # create a crawler and it's management task
        crawler = models.Crawler.objects.create(urls=urljoin(base_url, 'a'))
        task = models.CrawlerTask.objects.create(crawler=crawler)

        # send off the task
        task.send()

        # wait for the task to complete
        self.broker.join(task.task.queue_name)
        self.worker.join()

        # the task should be done
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.done)

        # ensure the index has been populated
        Index(crawler.index).refresh()

        # and there should be three crawled documents
        self.assertEqual(crawler.documents.count(), 3)
