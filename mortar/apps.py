from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save

from .documents import Document


class MortarConfig(AppConfig):
    name = 'mortar'

    def ready(self):
        Crawler = self.get_model('Crawler')

        post_save.connect(Document.create_index, sender=Crawler)
        post_delete.connect(Document.delete_index, sender=Crawler)
