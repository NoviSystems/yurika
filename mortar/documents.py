from django.conf import settings
from elasticsearch.helpers import bulk
from elasticsearch_dsl import DocType, connections, field


class DocBase(DocType):

    @classmethod
    def context(cls, using=None, index=None):
        return DocContext(cls, using, index)

    @classmethod
    def create(cls, doc, using=None, index=None, **kwargs):
        return doc.save(using, index, **kwargs)

    @classmethod
    def bulk_create(cls, docs, using=None, index=None, handler=bulk, **kwargs):
        if index is not None:
            for doc in docs:
                if not doc._doc_type.index:
                    doc._doc_type.index = index

        client = connections.get_connection(using or cls._doc_type.using)
        docs = [doc.to_dict(include_meta=True) for doc in docs]
        return handler(client, docs, **kwargs)


class Document(DocBase):
    url = field.Keyword()
    referer = field.Keyword()
    title = field.Text()
    html = field.Text()
    text = field.Text()
    timestamp = field.Date(default_timezone=settings.TIME_ZONE)


class Sentence(DocBase):
    document_id = field.Keyword()
    text = field.Text()


class Dictionary(DocBase):
    name = field.Keyword()
    terms = field.Keyword()

    class Meta:
        index = 'dictionaries'


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

    def create(self, doc, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.doc_type.create(doc, using, index, **kwargs)

    def bulk_create(self, docs, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.doc_type.bulk_create(docs, using, index, **kwargs)
