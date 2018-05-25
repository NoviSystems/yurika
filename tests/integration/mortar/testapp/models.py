from django.db import models
from django_fsm import transition

from yurika.mortar.models import Task


STATUS = Task.STATUS


class Finish(Task):
    flag = models.BooleanField(default=False)

    task_path = 'tests.integration.mortar.testapp.tasks.finish'

    @transition(field='status', source=STATUS.running, target=STATUS.done)
    def _finish(self):
        self.flag = True

        return super()._finish()


class Fail(Task):
    task_path = 'tests.integration.mortar.testapp.tasks.fail'


class Abort(Task):
    task_path = 'tests.integration.mortar.testapp.tasks.abort'
