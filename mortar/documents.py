from django.conf import settings
from elasticsearch import TransportError
from elasticsearch_dsl import DocType, Index, field


class Document(DocType):
    url = field.Text()
    referer = field.Text()
    title = field.Text()
    content = field.Text()
    timestamp = field.Date(default_timezone=settings.TIME_ZONE)

    @classmethod
    def create_index(cls, sender, instance, created, **kwargs):
        if created:
            idx = Index(instance.index)
            idx.doc_type = cls
            idx.create()

    @classmethod
    def delete_index(cls, sender, instance, **kwargs):
        idx = Index(instance.index)
        try:
            idx.delete()
        except TransportError:
            pass