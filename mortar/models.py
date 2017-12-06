from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from mptt.models import MPTTModel, TreeForeignKey
import django.db.models.options as options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('index_mapping', )

class Crawler(models.Model):
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=3, choices=(('txt', 'File System Crawler'),
                                                       ('web', 'Web Crawler')))
    index = models.ForeignKey('ElasticIndex', related_name='crawlers')
    seed_list = models.ManyToManyField('Seed', blank=True, related_name='crawlers')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=(('Running', 'Running'), ('Finished', 'Finished'),
                                                      ('Stopped', 'Stopped')))
    process_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return 'Crawler: %s' % self.name

    class Meta:
        index_mapping = {'settings': {'mappings': {'doc': {'properties': {'title': {'type': 'text'},
                                                          'content': {'type': 'text'},
                                                          'tstamp': {'type': 'date','format': 'yyyy-MM-dd HH:mm'},
                                                          'url': {'type': 'text'}}
                                           }
                                   }
                      }
         }


class Seed(models.Model):

    class Meta:
        verbose_name = 'Seed'


class URLSeed(Seed):
    url = models.URLField()

    def __str__(self):
        return 'URL: %s' % self.url


class FileSeed(Seed):
    path = models.FilePathField()

    def __str__(self):
        return 'Path: %s' % self.path


class ElasticIndex(models.Model):
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', 'Only alphanumeric characters are allowed')
    name = models.CharField(max_length=20, unique=True,  validators=[alphanumeric])

    def __str__(self):
        return self.name


class Tree(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    doc_source_index = models.ForeignKey('ElasticIndex', related_name='doc_sources')
    doc_dest_index = models.ForeignKey('ElasticIndex', related_name='doc_dests')

    def __str__(self):
        return 'Tree: %s' % self.name

    class Meta:
        index_mapping = {}


class Node(MPTTModel):
    name = models.CharField(max_length=50)
    regex = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    tree_link = models.ForeignKey('Tree', related_name='nodes')
    dictionary = models.ForeignKey('Dictionary', null=True, blank=True, related_name='nodes')

    @property
    def full_path_name(self):
        ancestors = self.get_ancestors()
        path = ''
        for ancestor in ancestors:
            if len(path) == 0:
                path = ancestor.name
            else:
                path = path + '.' +  ancestor.name
        return path

    class MPTTMeta:
        order_insertion_by = [
         'name']

    def __str__(self):
        return self.name


class Dictionary(models.Model):
    name = models.CharField(max_length=50)
    filepath = models.FilePathField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Dictionaries'


class Word(models.Model):
    name = models.CharField(max_length=255)
    dictionary = models.ForeignKey('Dictionary', related_name='words')

    def __str__(self):
        return self.name


class Document(models.Model):
    url = models.URLField()
    crawled_at = models.DateTimeField()
    index = models.ForeignKey('ElasticIndex', related_name='documents')
    tree = models.ForeignKey('Tree', related_name='documents')

    def __str__(self):
        return self.url


class Annotation(models.Model):
    content = models.TextField()
    tree = models.ForeignKey('Tree', related_name='annotations')
    document = models.ForeignKey('Document', related_name='annotations')
    category = models.CharField(max_length=1, choices=(('S', 'Sentence'), ('P', 'Paragraph'),
                                                       ('D', 'Document')))
    query = models.ForeignKey('Query', related_name='annotations')

    def __str__(self):
        return str(self.id)

    class Meta:
        index_mapping = {}


class Query(models.Model):
    name = models.CharField(max_length=50, blank=True)
    string = models.TextField(blank=True)
    elastic_json = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Queries'


class QueryPart(models.Model):
    query = models.ForeignKey('Query', related_name='parts')
    op = models.CharField(max_length=1, choices=(('+', 'AND'), ('|', 'OR')))
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class DictionaryPart(QueryPart):
    dictionary = models.ForeignKey('Dictionary', related_name='query_parts')


class RegexPart(QueryPart):
    regex = models.ForeignKey('Node', related_name='query_parts')


class SubQueryPart(QueryPart):
    subquery = models.ForeignKey('Query', related_name='query_parts')


class PartOfSpeechPart(QueryPart):
    part_of_speech = models.CharField(max_length=4, choices=settings.PARTS_OF_SPEECH)
