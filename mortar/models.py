from importlib import import_module

from celery import signals
from celery.task.control import revoke
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition
from model_utils import Choices, managers


def import_path(path):
    module, attr = path.rsplit('.', 1)
    module = import_module(module)

    return getattr(module, attr)


@signals.task_prerun.connect
def start(sender, task_id, task, args, kwargs, **kw):
    try:
        # Note that `kwargs['task_id']` is the Task's primary key value, and
        # the `task_id` argument is the Celery task ID, which is saved under
        # the same name on the task model.
        task = Task.objects.select_subclasses().get(pk=kwargs.get('task_id'))
    except Task.DoesNotExist:
        return

    task._start(task_id)
    task.save()


@signals.task_postrun.connect
def finish(sender, task_id, task, args, kwargs, retval, state, **kw):
    # ignore task failures, handled by abort/error handlers
    if not state == 'SUCCESS':
        return

    try:
        task = Task.objects.select_subclasses().get(pk=kwargs.get('task_id'))
    except Task.DoesNotExist:
        return

    task._finish()
    task.save()


@signals.task_revoked.connect
def abort(sender, request, terminated, **kw):
    try:
        task = Task.objects.select_subclasses().get(pk=request.task_id)
    except Task.DoesNotExist:
        return

    task._abort()
    task.save()


@signals.task_failure.connect
def error(sender, task_id, exception, args, kwargs, traceback, **kw):
    try:
        task = Task.objects.select_subclasses().get(pk=kwargs.get('task_id'))
    except Task.DoesNotExist:
        return

    task._error()
    task.save()


class Task(models.Model):
    """
    Base class for models that represent a process/task. Controls and tracks
    the status of celery task objects. Note that the state transitions are
    controlled through celery's signal handlers, and they should not be invoked
    directly.

    The public API consists of the `task` property, which generates a task
    signature, and the `.abort()` method, which can be used to revoke
    long-running tasks.

        >>> task = MyTask.objects.create()
        >>> task.task.apply_async()
        ...
        >>> task.refresh_from_db()
        >>> task.abort()
        ...
        >>> task.refresh_from_db()
        >>> task.status
        'aborted'

    """
    STATUS = Choices(
        ('not_started', 'Not Started'),
        ('running', 'Running'),
        ('finished', 'Finished'),
        ('aborted', 'Aborted'),
        ('errored', 'Error Occurred'),
    )

    task_id = models.UUIDField(null=True, default=None, editable=False,
                               help_text="Celery task ID")
    status = FSMField(choices=STATUS, default=STATUS.not_started, editable=False)
    started_at = models.DateTimeField(null=True, editable=False)
    finished_at = models.DateTimeField(null=True, editable=False)

    objects = managers.InheritanceManager()

    @property
    def task_path(self):
        raise NotImplementedError

    @property
    def task(self):
        task = import_path(self.task_path)

        # immutable arg prevents results from being passed in task chain
        return task.signature([], {'task_id': self.pk}, immutable=True)

    def abort(self, *, signal='SIGTERM'):
        revoke(self.task_id, terminate=True, signal=signal)

    @transition(field=status, source=STATUS.not_started, target=STATUS.running)
    def _start(self, task_id):
        # """
        # Start the task. A `task` may be provided, which is useful in cases where
        # several tasks may need to be chained.
        # """
        assert self.task_id is None

        self.task_id = task_id
        self.started_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.finished)
    def _finish(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.aborted)
    def _abort(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.errored)
    def _error(self):
        self.finished_at = timezone.now()

    def log_error(self, error, error_type=None):
        return self.errors.create(message=error, type=error_type)

    def clear_errors(self):
        self.errors.delete()


class TaskError(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='errors')
    timestamp = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    type = models.CharField(max_length=32, null=True, blank=True)

    def __str__(self):
        if self.type:
            return "Task Error {}: {}".format(self.type, self.message)
        return "Task Error: {}".format(self.message)
