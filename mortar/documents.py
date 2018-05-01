from django.conf import settings
from elasticsearch import TransportError
from elasticsearch_dsl import DocType, Index, field


class DocBase(DocType):

    @classmethod
    def context(cls, using=None, index=None):
        return DocContext(cls, using, index)


class Document(DocBase):
    url = field.Text()
    referer = field.Text()
    title = field.Text()
    html = field.Text()
    text = field.Text()
    timestamp = field.Date(default_timezone=settings.TIME_ZONE)

    @classmethod
    def create_index(cls, sender, instance, created, **kwargs):
        if created:
            idx = Index(instance.index_name)
            idx.doc_type = cls
            idx.create()

    @classmethod
    def delete_index(cls, sender, instance, **kwargs):
        idx = Index(instance.index_name)
        try:
            idx.delete()
        except TransportError:
            pass


class DocContext(object):
    def __init__(self, doc_type, using=None, index=None):
        self.doc_type = doc_type
        self.using = using or doc_type._doc_type.using
        self.index = index or doc_type._doc_type.index

    def search(self, using=None, index=None):
        using = using or self.using
        index = index or self.index
        return self.doc_type.search(using, index)

    def get(self, id, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.doc_type.get(id, using, index, **kwargs)

    def mget(self, docs, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.doc_type.mget(docs, using, index, **kwargs)
