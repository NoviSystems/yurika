from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'yurika.utils'

    def ready(self):
        # system checks
        from . import checks  # noqa
