import dramatiq

from . import models


@dramatiq.actor(max_retries=0)
def finish(task_id):
    return models.Finish.objects.get(id=task_id)


@dramatiq.actor(max_retries=0)
def fail(task_id):
    raise Exception


@dramatiq.actor(max_retries=0)
def abort(task_id):
    raise models.Task.Abort
