import unittest
from unittest.mock import patch

from django.test import TestCase, override_settings

from mortar.models import Task

from .testapp import models


STATUS = Task.STATUS


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_TASK_ALWAYS_EAGER=True, )
class TaskTransitionTests(TestCase):

    def test_finished(self):
        task = models.Finished.objects.create()

        self.assertEqual(task.status, STATUS.not_started)
        task.task.apply_async()
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.finished)

    @patch('celery.app.trace.logger')
    def test_errored(self, mock_logger):
        task = models.Errored.objects.create()

        self.assertEqual(task.status, STATUS.not_started)
        task.task.apply_async()
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.errored)

        # We cannot trivially perform more comprehensive assertions on logging
        # calls, as celery calls `.log` instead of the appropriate helper.
        mock_logger.log.assert_called_once()

    def test_inheritance(self):
        """
        Ensure child tasks can override the transition methods.
        `Finished._finish` sets `flag`.
        """
        task = models.Finished.objects.create()

        self.assertEqual(task.status, STATUS.not_started)
        self.assertFalse(task.flag)
        task.task.apply_async()
        task.refresh_from_db()
        self.assertEqual(task.status, STATUS.finished)
        self.assertTrue(task.flag)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   CELERY_TASK_ALWAYS_EAGER=True, )
class TaskChainTests(TestCase):

    def test_successful_chain(self):
        task1 = models.Finished.objects.create()
        task2 = models.Finished.objects.create()

        chain = task1.task | task2.task
        chain.apply_async()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.finished)
        self.assertEqual(task2.status, STATUS.finished)

    @patch('celery.app.trace.logger')
    def test_success_then_error(self, mock_logger):
        task1 = models.Finished.objects.create()
        task2 = models.Errored.objects.create()

        chain = task1.task | task2.task
        chain.apply_async()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.finished)
        self.assertEqual(task2.status, STATUS.errored)

        mock_logger.log.assert_called_once()

    @patch('celery.app.trace.logger')
    @unittest.expectedFailure
    def test_error_revokes_remainder(self, mock_logger):
        """
        Test is currently broken, as the task error is unexpectedly raised.
        It is not clear if this is an issue with celery generally, or only if
        when it's operating in synchronous/EAGER mode.
        """
        task1 = models.Errored.objects.create()
        task2 = models.Finished.objects.create()

        chain = task1.task | task2.task
        chain.apply_async()

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, STATUS.errored)
        self.assertEqual(task2.status, STATUS.aborted)

        mock_logger.log.assert_called_once()
