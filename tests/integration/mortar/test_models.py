import logging
from contextlib import contextmanager

from django.test import TestCase
from django_dramatiq.test import DramatiqTestCase

from mortar.models import Task

from .testapp import models


STATUS = Task.STATUS


@contextmanager
def disable_logging(name):
    logger = logging.getLogger(name)
    level = logger.level
    logger.setLevel(logging.CRITICAL)
    yield
    logger.setLevel(level)


class TaskTransitionTests(DramatiqTestCase):

    def test_finish(self):
        task = models.Finish.objects.create()

        self.assertEqual(task.status, STATUS.not_queued)
        task.send()

        self.broker.join(task.task.queue_name)
        self.worker.join()

        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.done)

    @disable_logging('dramatiq.middleware.retries.Retries')
    @disable_logging('dramatiq.worker.WorkerThread')
    def test_fail(self):
        task = models.Fail.objects.create()

        self.assertEqual(task.status, STATUS.not_queued)
        task.send()

        self.broker.join(task.task.queue_name)
        self.worker.join()

        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.failed)

    @disable_logging('dramatiq.middleware.retries.Retries')
    @disable_logging('dramatiq.worker.WorkerThread')
    def test_abort(self):
        task = models.Abort.objects.create()

        self.assertEqual(task.status, STATUS.not_queued)
        task.send()

        self.broker.join(task.task.queue_name)
        self.worker.join()

        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.aborted)

    def test_inheritance(self):
        """
        Ensure child tasks can override the transition methods.
        `Finish._finish` sets `flag`.
        """
        task = models.Finish.objects.create()

        self.assertEqual(task.status, STATUS.not_queued)
        self.assertFalse(task.flag)
        task.send()

        self.broker.join(task.task.queue_name)
        self.worker.join()

        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.done)
        self.assertTrue(task.flag)


class TaskChainTests(DramatiqTestCase):

    def test_successful_chain(self):
        task1 = models.Finish.objects.create()
        task2 = models.Finish.objects.create()

        chain = task1.message() | task2.message()
        chain.run()

        self.broker.join(task1.task.queue_name)
        self.broker.join(task2.task.queue_name)
        self.worker.join()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.done)
        self.assertEqual(task2.status, STATUS.done)

    @disable_logging('dramatiq.middleware.retries.Retries')
    @disable_logging('dramatiq.worker.WorkerThread')
    def test_success_then_error(self):
        task1 = models.Finish.objects.create()
        task2 = models.Fail.objects.create()

        chain = task1.message() | task2.message()
        chain.run()

        self.broker.join(task1.task.queue_name)
        self.broker.join(task2.task.queue_name)
        self.worker.join()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.done)
        self.assertEqual(task2.status, STATUS.failed)

    @disable_logging('dramatiq.middleware.retries.Retries')
    @disable_logging('dramatiq.worker.WorkerThread')
    def test_error_revokes_remainder(self):
        task1 = models.Fail.objects.create()
        task2 = models.Finish.objects.create()

        chain = task1.message() | task2.message()
        chain.run()

        self.broker.join(task1.task.queue_name)
        self.broker.join(task2.task.queue_name)
        self.worker.join()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.failed)
        self.assertEqual(task2.status, STATUS.not_queued)


class ErrorHandlingTests(TestCase):

    def test_log_error(self):
        task = models.Finish.objects.create()
        task.log_error('!!!')

        error = task.errors.get()
        self.assertEqual(error.message, '!!!')
        self.assertEqual(error.traceback, '')

    def test_log_exception(self):
        task = models.Finish.objects.create()
        try:
            raise Exception('!!!')
        except Exception as e:
            task.log_exception(e)

        error = task.errors.get()
        self.assertEqual(error.message, '!!!')
        self.assertIn("Traceback (most recent call last):\n", error.traceback)
        self.assertIn(", in test_log_exception\n", error.traceback)
        self.assertIn("    raise Exception('!!!')\n", error.traceback)
        self.assertIn("Exception: !!!\n", error.traceback)
