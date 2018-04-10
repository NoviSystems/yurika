from django.conf import settings
from dramatiq import middleware
from raven.contrib.django import models as raven

from .models import Task


class SentryMiddleware(middleware.Middleware):
    """
    Log uncaught exceptions to Sentry (if configured).
    """

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if hasattr(settings, 'RAVEN_CONFIG') and exception is not None:
            raven.client.captureException()


class TaskStatusMiddleware(middleware.Middleware):
    """
    Track the status of a task's execution.
    """

    def before_enqueue(self, broker, message, delay):
        try:
            task = Task.downcast.get(pk=message.kwargs.get('task_id'))
        except Task.DoesNotExist:
            return

        task._enqueue(message.message_id)
        task.save()

    def before_process_message(self, broker, message):
        try:
            task = Task.downcast.get(pk=message.kwargs.get('task_id'))
        except Task.DoesNotExist:
            return

        task._start()
        task.save()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        try:
            task = Task.downcast.get(pk=message.kwargs.get('task_id'))
        except Task.DoesNotExist:
            return

        if exception is None:
            task._finish()
        elif isinstance(exception, task.Abort):
            task._abort()
        else:
            task.log_exception(exception)
            task._fail()

        task.save()
