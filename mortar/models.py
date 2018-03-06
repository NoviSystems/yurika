"""
BSD 3-Clause License

Copyright (c) 2018, North Carolina State University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. The names "North Carolina State University", "NCSU" and any trade‐name,
   personal name, trademark, trade device, service mark, symbol, image, icon,
   or any abbreviation, contraction or simulation thereof owned by North
   Carolina State University must not be used to endorse or promoteproducts
   derived from this software without prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from itertools import groupby

import elasticsearch
from celery.task.control import revoke
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import options
from django.utils import timezone
from model_utils import Choices, managers
from mptt.models import MPTTModel, TreeForeignKey


options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('index_mapping', )


class Analysis(models.Model):
    crawler = models.ForeignKey('Crawler', related_name="analyses", null=True, blank=True)
    mindmap = models.ForeignKey('Tree', related_name="analyses", null=True, blank=True)
    query = models.ForeignKey('Query', related_name="analyses", null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    crawler_configured = models.BooleanField(default=False)
    mindmap_configured = models.BooleanField(default=False)
    dicts_configured = models.BooleanField(default=False)
    query_configured = models.BooleanField(default=False)
    # status = models.IntegerField(default=0, choices=(
    #     (0, 'Not Configured'),
    #     (1, 'Crawler Configured'),
    #     (2, 'MindMap Configured'),
    #     (3, 'Dictionaries Configured'),
    #     (4, 'Query Configured'),
    #     (5, 'Crawling'),
    #     (6, 'Preprocessing'),
    #     (7, 'Querying'),
    #     (8, 'Finished'),
    #     (9, 'Stopped'),
    # ))

    @property
    def all_configured(self):
        return self.crawler_configured and self.mindmap_configured and self.dicts_configured and self.query_configured

    @property
    def crawler_running(self):
        return self.crawler.process_id is not None

    @property
    def preprocess_running(self):
        return self.mindmap.process_id is not None

    @property
    def query_running(self):
        return self.query.process_id is not None

    @property
    def any_running(self):
        return self.crawler_running or self.preprocess_running or self.query_running

    @property
    def all_finished(self):
        return self.finished_at is not None and not self.any_running

    def stop(self):
        if self.crawler_running:
            if self.crawler.process_id:
                # Send SIGABRT instead of SIGTERM to crawler. Scrapy catches
                # SIGTERM and cleanly exits the crawler, but here we need the
                # task to fail so the next task in the chain (preprocessing)
                # doesn't run.
                revoke(self.crawler.process_id, terminate=True, signal="SIGABRT")
                self.crawler.process_id = None
                self.crawler.finished_at = timezone.now()
                self.crawler.status = 2
                self.crawler.save()
        if self.preprocess_running:
            if self.mindmap.process_id:
                revoke(self.mindmap.process_id, terminate=True)
                self.mindmap.process_id = None
                self.mindmap.finished_at = timezone.now()
                self.mindmap.save()
        if self.query_running:
            if self.query.process_id:
                revoke(self.query.process_id, terminate=True)
                self.query.process_id = None
                self.query.finished_at = timezone.now()
                self.query.save()

        self.finished_at = timezone.now()
        self.save()

    def clear_results(self):
        self.stop()

        if self.crawler:
            self.crawler.clear_errors()
            self.crawler.started_at = None
            self.crawler.finished_at = None
            self.crawler.status = 2
            self.crawler.save()
        if self.mindmap:
            self.mindmap.clear_errors()
            self.mindmap.started_at = None
            self.mindmap.finished_at = None
            self.mindmap.save()
        if self.query:
            self.query.clear_errors()
            self.query.started_at = None
            self.query.finished_at = None
            self.query.save()

        es = settings.ES_CLIENT
        es.indices.delete(index='source', ignore=[400, 404])
        es.indices.delete(index='dest', ignore=[400, 404])

        annotations = Annotation.objects.using('explorer').filter(analysis_id=self.id)
        annotations.delete()

        self.save()

    def clear_config(self):
        self.clear_results()

        if self.crawler:
            self.crawler.delete()
        if self.mindmap:
            self.mindmap.delete()
        if self.query:
            self.query.delete()

        self.delete()


class Crawler(models.Model):
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=3, choices=(('txt', 'File System Crawler'),
                                                       ('web', 'Web Crawler')))
    index = models.ForeignKey('ElasticIndex', related_name='crawlers')
    seed_list = models.ManyToManyField('Seed', blank=True, related_name='crawlers')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(default=2, choices=((0, 'Running'), (1, 'Finished'), (2, 'Stopped')))
    process_id = models.CharField(max_length=50, null=True, blank=True)

    def clear_errors(self):
        self.errors.delete()

    def log_error(self, error, error_type=None):
        ExecuteError.log_error(self.analyses.first(), 0, error, error_type)

    @property
    def errors(self):
        return ExecuteError.objects.filter(step=0, analysis=self.analyses.first())

    @property
    def count(self):
        es = settings.ES_CLIENT
        try:
            return es.count(index=self.index.name).get('count')
        except elasticsearch.exceptions.NotFoundError as e:
            if e.error == 'index_not_found_exception':
                return 0  # ElasticSeach index not created yet
            else:
                raise

    def __str__(self):
        return 'Crawler: %s' % self.name

    class Meta:
        index_mapping = {
            'settings': {
                'mappings': {
                    'doc': {
                        'properties': {
                            'title': {'type': 'text'},
                            'content': {'type': 'text'},
                            'tstamp': {'type': 'date', 'format': 'yyyy-MM-dd HH:mm'},
                            'url': {'type': 'text'},
                        }
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
    name = models.CharField(max_length=20, unique=True, validators=[alphanumeric])

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

    def clear_errors(self):
        self.errors.delete()

    def log_error(self, error, error_type=None):
        ExecuteError.log_error(self.analyses.first(), 1, error, error_type)

    @property
    def errors(self):
        return ExecuteError.objects.filter(step=1, analysis=self.analyses.first())

    @property
    def n_processed(self):
        es = settings.ES_CLIENT
        try:
            return es.count(index=self.doc_dest_index.name, doc_type="doc").get('count')
        except elasticsearch.exceptions.NotFoundError as e:
            if e.error == 'index_not_found_exception':
                return 0  # ElasticSeach index not created yet
            else:
                raise

    @property
    def n_total(self):
        es = settings.ES_CLIENT
        try:
            return es.count(index=self.doc_source_index.name).get('count')
        except elasticsearch.exceptions.NotFoundError as e:
            if e.error == 'index_not_found_exception':
                return 0  # ElasticSeach index not created yet
            else:
                raise

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
                path = path + '.' + ancestor.name
        return path

    class MPTTMeta:
        order_insertion_by = ['name']

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
    category = models.IntegerField(choices=((0, 'Sentence'), (1, 'Paragraph'), (2, 'Document')))
    query_id = models.IntegerField()

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "annotations"
        index_mapping = {}


class Query(models.Model):
    CATEGORY = Choices(
        (0, 'sentence', 'Sentence'),
        (1, 'paragraph', 'Paragraph'),
        (2, 'document', 'Document'),
    )
    name = models.CharField(max_length=50, blank=True)
    category = models.IntegerField(choices=CATEGORY)

    # TODO: separate into a QueryRun model
    elastic_json = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    process_id = models.CharField(max_length=50, null=True, blank=True)

    @property
    def status(self):
        if self.started_at is None:
            return 2  # Stopped
        elif self.process_id:
            return 0  # Running
        else:
            return 1  # Finished

    def clear_errors(self):
        self.errors.delete()

    def log_error(self, error, error_type=None):
        ExecuteError.log_error(self.analyses.first(), 2, error, error_type)

    @property
    def errors(self):
        return ExecuteError.objects.filter(step=2, analysis=self.analyses.first())

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Queries'

    def json(self):
        """
        Return a json structure that represents an Elasticsearch bool query. Its
        query parts are grouped by their `occurance` in the query.
        """
        return {'bool': {
            occurance: [part.json() for part in parts]
            for occurance, parts
            in groupby(self.parts.select_subclasses(), lambda o: o.occurance)
        }}


class QueryPart(models.Model):
    OCCURANCE = Choices(
        # value, display value
        ('must', 'Must occur'),
        ('should', 'Should occur'),
        ('must_not', 'Must not occur'),
    )

    query = models.ForeignKey('Query', related_name='parts')
    occurance = models.CharField(max_length=8, choices=OCCURANCE)

    objects = managers.InheritanceManager()

    class Meta:
        ordering = ['pk']

    def json(self):
        """
        Return a json structure that represents an Elasticsearch query clause.

        Note that the `occurance` is used to group json clauses, and should not
        be present in this output.
        """
        raise NotImplementedError


class DictionaryPart(QueryPart):
    dictionary = models.ForeignKey('Dictionary', related_name='+')

    def json(self):
        return {
            'terms': {
                'content': {
                    'index': 'dictionaries',
                    'type': 'dictionary',
                    'id': self.dictionary_id,
                    'path': 'words',
                }
            }
        }


class NodePart(QueryPart):
    node = models.ForeignKey('Node', related_name='+')

    def json(self):
        content = self.node.regex if self.node.regex else self.node.name

        return {'regexp': {'content': content}}


class SubQueryPart(QueryPart):
    subquery = models.ForeignKey('Query', related_name='+')

    def json(self):
        return self.subquery.json()


class PartOfSpeechPart(QueryPart):
    PARTS_OF_SPEECH = Choices(
        ('CC', 'Coordinating Conjunction'),
        ('CD', 'Cardinal Number'),
        ('DT', 'Determiner'),
        ('EX', 'Existential there'),
        ('FW', 'Foreign Word'),
        ('IN', 'Preposition of subordinating conjunction'),
        ('JJ', 'Adjective'),
        ('JJR', 'Adjective, comparitive'),
        ('JJS', 'Adjective, superlative'),
        ('LS', 'List item marker'),
        ('MD', 'Modal'),
        ('NN', 'Noun, singular or mass'),
        ('NNS', 'Noun, plural'),
        ('NNP', 'Proper Noun, singular'),
        ('NNPS', 'Proper Noun, plural'),
        ('PDT', 'Predeterminer'),
        ('POS', 'Possessive ending'),
        ('PRP', 'Personal pronoun'),
        ('PRP$', 'Possessive pronoun'),
        ('RB', 'Adverb'),
        ('RBR', 'Adverb, comparative'),
        ('RBS', 'Adverb, superlative'),
        ('RP', 'Particle'),
        ('SYM', 'Symbol'),
        ('TO', 'to'),
        ('UH', 'Interjection'),
        ('VB', 'Verb, base form'),
        ('VBD', 'Verb, past tense'),
        ('VBG', 'Verb, gerund or present participle'),
        ('VBN', 'Verb, past participle'),
        ('VBP', 'Verb, non-3rd person singular present'),
        ('VBZ', 'Verb 3rd person singular present'),
        ('WDT', 'Wh-determiner'),
        ('WP', 'Wh-pronoun'),
        ('WP$', 'Possessive wh-pronoun'),
        ('WRB', 'Wh-adverb'),
    )
    part_of_speech = models.CharField(max_length=4, choices=PARTS_OF_SPEECH)

    def json(self):
        return {'match': {'tokens': '|' + self.part_of_speech}}


class RegexPart(QueryPart):
    regex = models.CharField(max_length=64)

    def json(self):
        return {'regexp': {'content': self.regex}}


class ExecuteError(models.Model):
    STEP_CHOICES = (
        (0, "Crawling"),
        (1, "Processing"),
        (2, "Querying"),
    )

    step = models.IntegerField(choices=STEP_CHOICES)
    time = models.DateTimeField(default=timezone.now)
    msg = models.TextField()
    error_type = models.CharField(max_length=32, null=True, blank=True)
    analysis = models.ForeignKey('Analysis', related_name='errors')

    def __str__(self):
        # step_str = dict(self.STEP_CHOICES)[self.step]
        # type_str = " {}".format(self.error_type) if self.error_type else ""
        # return "{} Error{}: {}".format(step_str, type_str, self.msg)
        return self.msg

    @classmethod
    def log_error(cls, analysis, step, error, error_type=None):
        e = ExecuteError(
            step=step,
            msg=error,
            error_type=error_type,
            analysis=analysis,
        )
        e.save()
