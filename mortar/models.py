import os
import shutil
import uuid
from importlib import import_module
from traceback import format_exception

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django_fsm import FSMField, transition
from elasticsearch_dsl import Index
from model_utils import Choices, managers
from shortuuid import ShortUUID

from mortar import documents
from project import utils


# Elasticsearch-friendly identifiers (no uppercase characters)
b36_uuid = ShortUUID(alphabet='0123456789abcdefghijklmnopqrstuvwxyz')


def import_path(path):
    module, attr = path.rsplit('.', 1)
    module = import_module(module)

    return getattr(module, attr)


class CastingManager(managers.InheritanceManager):
    """
    Manager that automatically downcasts instances to their inherited types.
    """

    def get_queryset(self):
        return super().get_queryset().select_subclasses()


class Task(models.Model):
    """
    Base class for models that represent a self-contained process/task. The
    actor function should return no value and accept the Task instance's primary
    key as its only argument. Any configuration should be provided through
    related database models.

    The task's status transitions are handled by `mortar.middleware.TaskStatus`,
    and the transition methods should not be invoked directly.

    The public API consists of `send`ing the task, or composing as a `message`
    in a Dramatiq `pipeline`. Additionally, the actor may self-terminate by
    raising `Task.Abort`.

        >>> task = MyTask.objects.create()
        >>> task.send()
        ...
        >>> task.refresh_from_db()
        >>> task.status
        'running'
        ...
        >>> task.refresh_from_db()
        >>> task.status
        'done'

    """
    STATUS = Choices(
        ('not_queued', 'Not queued'),
        ('enqueued', 'Waiting'),
        ('running', 'Running'),
        ('failed', 'Error Occurred'),
        ('done', 'Finished'),

        # non-standard state
        ('aborted', 'Aborted'),
    )

    message_id = models.UUIDField(null=True, default=None, editable=False,
                                  help_text="Dramatiq message ID")
    status = FSMField(choices=STATUS, default=STATUS.not_queued, editable=False)
    started_at = models.DateTimeField(null=True, editable=False)
    finished_at = models.DateTimeField(null=True, editable=False)

    objects = managers.InheritanceManager()
    downcast = CastingManager()

    class Meta:
        base_manager_name = 'downcast'

    class Abort(Exception):
        pass

    @property
    def task_path(self):
        """
        The module path of the task function. This property must be implemented.
        """
        raise NotImplementedError

    @cached_property
    def task(self):
        return import_path(self.task_path)

    def message(self, **options):
        """
        Create a message for composition in a pipeline or group.
        """
        # pipe_ignore arg prevents results from being passed along the pipeline.
        # tasks must be self contained and return no result.
        options['pipe_ignore'] = True
        return self.task.message_with_options(
            kwargs={'task_id': self.pk},
            **options
        )

    def send(self, **options):
        """
        Send a message to the broker for processing.
        """
        return self.task.send_with_options(
            kwargs={'task_id': self.pk},
            **options
        )

    def revoke(self):
        """
        Signal a task to self-abort. This feature is not provided by default,
        and it is necessary to implement a method by which the the Task subclass
        signals to the task function to raise `Task.Abort`.
        """
        raise NotImplementedError

    @transition(field=status, source=STATUS.not_queued, target=STATUS.enqueued)
    def _enqueue(self, message_id):
        assert self.message_id is None

        self.message_id = message_id

    @transition(field=status, source=STATUS.enqueued, target=STATUS.running)
    def _start(self):
        self.started_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.done)
    def _finish(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.failed)
    def _fail(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.aborted)
    def _abort(self):
        self.finished_at = timezone.now()

    def log_error(self, error):
        return self.errors.create(message=error)

    def log_exception(self, exc):
        # Note: first argument is ignore since python 3.5
        traceback = ''.join(format_exception(None, exc, exc.__traceback__))
        return self.errors.create(message=str(exc), traceback=traceback)

    def clear_errors(self):
        self.errors.delete()


class TaskError(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='errors')
    timestamp = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    traceback = models.TextField()

    def __str__(self):
        return "Task Error: {}".format(self.message)


class Crawler(models.Model):
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    urls = models.TextField(help_text="List of URLs to crawl (separated by newlines).")

    def __str__(self):
        return 'Crawler: %s' % self.pk

    def resume(self):
        """
        Resume the crawler from where it left off. It is assumed the
        state directory was not cleared by the user.

        Note: the crawler task still needs to be re-queued.
        """
        self.task.delete()
        self.task = CrawlerTask.objects.create(crawler=self)

    def restart(self):
        """
        Restart the crawler by clearing its existing state. The index is not
        cleared, and will contain updated, duplicate responses.

        Note: the crawler task still needs to be re-queued.
        """
        if os.path.exists(self.state_dir):
            shutil.rmtree(self.state_dir)

        self.task.delete()
        self.task = CrawlerTask.objects.create(crawler=self)

    @property
    def state_dir(self):
        """
        Directory where crawler state/persistence data is stored.
        """
        return utils.path(f'.crawlers/{self.uuid}')

    @property
    def index_name(self):
        return b36_uuid.encode(self.uuid)

    @property
    def index(self):
        return Index(self.index_name)

    @property
    def documents(self):
        return documents.Document.search(index=self.index_name)


class CrawlerTask(Task):
    crawler = models.OneToOneField(Crawler, on_delete=models.CASCADE, related_name='task')
    revoked = models.BooleanField(default=False, editable=False,
                                  help_text="Task has been marked for revocation.")

    @property
    def task_path(self):
        return 'mortar.tasks.crawl'

    def revoke(self):
        self.revoked = True
        self.save(update_fields=['revoked'])


@receiver(post_save, sender=Crawler)
def crawler_task(sender, instance, created, **kwargs):
    if created:
        CrawlerTask.objects.create(crawler=instance)
