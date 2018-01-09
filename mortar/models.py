from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from mptt.models import MPTTModel, TreeForeignKey
import django.db.models.options as options
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('index_mapping', )

class Analysis(models.Model):
    crawler = models.ForeignKey('Crawler', related_name="analyses", null=True, blank=True) 
    mindmap = models.ForeignKey('Tree', related_name="analyses", null=True, blank=True)
    query = models.ForeignKey('Query', related_name="analyses", null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=0, choices=((0, 'Not Configured'), (1, 'Crawler Configured'), (2, 'MindMap Configured'), (3, 'Dictionaries Configured'), (4, 'Query Configured'), (5, 'Crawling'), (6, 'Preprocessing'), (7, 'Querying'), (8, 'Finished'), (9, 'Stopped')))

class Crawler(models.Model):
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=3, choices=(('txt', 'File System Crawler'),
                                                       ('web', 'Web Crawler')))
    index = models.ForeignKey('ElasticIndex', related_name='crawlers')
    seed_list = models.ManyToManyField('Seed', blank=True, related_name='crawlers')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=2, choices=((0, 'Running'), (1, 'Finished'),
                                                      (2, 'Stopped')))
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
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    process_id = models.CharField(max_length=50, null=True, blank=True)

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
    words = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Dictionaries'


class Document(models.Model):
    url = models.URLField()
    crawled_at = models.DateTimeField()
    index = models.ForeignKey('ElasticIndex', related_name='documents')
    tree = models.ForeignKey('Tree', related_name='documents')

    def __str__(self):
        return self.url


class Annotation(models.Model):
    content = models.TextField()
    analysis_id = models.IntegerField()
    document_id = models.IntegerField()
    category = models.IntegerField(choices=((0, 'Sentence'), (1, 'Paragraph'),
                    (2, 'Document')))
    query_id = models.IntegerField()

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "annotations"
        index_mapping = {}


class Query(models.Model):
    name = models.CharField(max_length=50, blank=True)
    string = models.TextField(blank=True)
    elastic_json = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    process_id = models.CharField(max_length=50, null=True, blank=True)
    category = models.IntegerField(choices=((0, 'Sentence'), (1, 'Paragraph'),(2, 'Document')), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Queries'


class QueryPart(models.Model):
    query = models.ForeignKey('Query', related_name='parts')
    op = models.IntegerField(choices=((1, 'AND'), (0, 'OR')))
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
