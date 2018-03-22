from celery import shared_task

from . import models


@shared_task()
def finished(task_id):
    return models.Finished.objects.get(id=task_id)


@shared_task()
def errored(task_id):
    raise Exception
