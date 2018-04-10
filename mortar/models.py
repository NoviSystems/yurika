from importlib import import_module

from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django_fsm import FSMField, transition
from model_utils import Choices, managers
from shortuuid import ShortUUID


def b36_uuid():
    # Use a function so migrations don't recompute on ShortUUID.
    # Elasticsearch-friendly identifiers (no uppercase characters)
    b36 = ShortUUID(alphabet='0123456789abcdefghijklmnopqrstuvwxyz')
    return b36.uuid()


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

    def abort(self):
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

    def clear_errors(self):
        self.errors.delete()


class TaskError(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='errors')
    timestamp = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    traceback = models.TextField()

    def __str__(self):
        if self.type:
            return "Task Error {}: {}".format(self.type, self.message)
        return "Task Error: {}".format(self.message)


class Crawler(models.Model):
    index = models.UUIDField(unique=True, editable=False, default=b36.uuid,
                             help_text="Elasticsearch index name for crawled documents.")

    def __str__(self):
        return 'Crawler: %s' % self.pk


class URLSeed(models.Model):
    crawler = models.ForeignKey(Crawler, on_delete=models.CASCADE, related_name='seeds')
    url = models.URLField()


class CrawlerTask(Task):
    crawler = models.OneToOneField(Crawler, on_delete=models.CASCADE, related_name='task')

    @property
    def task_path(self):
        return 'mortar.tasks.crawl'

    def abort(self, *, clean=True):
        """
        Either abort the crawler cleanly, or not. A clean abort will allow
        subsequent celery tasks to complete, while an unclean abort will kill
        the remainder of the task chain.

        A clean abort is useful when you want to end crawling, but then start
        subsequent tasks (like preprocessing). The caveat is that a clean abort
        takes a few seconds for Scrapy to shutdown the crawler and exit, while
        an unclean abort is immediate.
        """
        super().abort(signal='SIGTERM' if clean else 'SIGABRT')
