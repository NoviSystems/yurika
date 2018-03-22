from django.db import models
from django_fsm import transition

from mortar.models import Task


STATUS = Task.STATUS


class Finished(Task):
    flag = models.BooleanField(default=False)

    task_path = 'tests.integration.mortar.testapp.tasks.finished'

    @transition(field='status', source=STATUS.running, target=STATUS.finished)
    def _finish(self):
        self.flag = True

        return super()._finish()


class Errored(Task):
    task_path = 'tests.integration.mortar.testapp.tasks.errored'
