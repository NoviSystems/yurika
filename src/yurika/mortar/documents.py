from django.conf import settings
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Document, connections, field


class BaseDocument(Document):

    @classmethod
    def context(cls, using=None, index=None):
        return DocumentContext(cls, using, index)

    @classmethod
    def create(cls, doc, using=None, index=None, **kwargs):
        return doc.save(using, index, **kwargs)

    @classmethod
    def bulk_create(cls, docs, using=None, index=None, handler=bulk, **kwargs):
        if index is not None:
            for doc in docs:
                doc._index = doc._index.clone(name=index)

        client = connections.get_connection(using or cls._index._using)
        docs = [doc.to_dict(include_meta=True) for doc in docs]
        return handler(client, docs, **kwargs)


class Document(BaseDocument):
    url = field.Keyword()
    referer = field.Keyword()
    title = field.Text()
    html = field.Text()
    text = field.Text()
    timestamp = field.Date(default_timezone=settings.TIME_ZONE)


class Sentence(BaseDocument):
    document_id = field.Keyword()
    text = field.Text()


class Dictionary(BaseDocument):
    name = field.Keyword()
    terms = field.Keyword()

    class Index:
        name = 'dictionaries'


class DocumentContext:
    def __init__(self, document_cls, using=None, index=None):
        self.document_cls = document_cls
        self.using = using or document_cls._index._using
        self.index = index or document_cls._index._name

    def search(self, using=None, index=None):
        using = using or self.using
        index = index or self.index
        return self.document_cls.search(using, index)

    def get(self, id, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.document_cls.get(id, using, index, **kwargs)

    def mget(self, docs, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.document_cls.mget(docs, using, index, **kwargs)

    def create(self, doc, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.document_cls.create(doc, using, index, **kwargs)

    def bulk_create(self, docs, using=None, index=None, **kwargs):
        using = using or self.using
        index = index or self.index
        return self.document_cls.bulk_create(docs, using, index, **kwargs)
