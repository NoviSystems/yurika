import json
import os
import shutil
import uuid
from traceback import format_exception

import jsonfield
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django_fsm import FSMField, transition
from elasticsearch import TransportError
from elasticsearch_dsl import Index
from model_utils import Choices, managers
from shortuuid import ShortUUID

from mortar import documents
from project import utils
from project.utils import validators


# Elasticsearch-friendly identifiers (no uppercase characters)
b36_uuid = ShortUUID(alphabet='0123456789abcdefghijklmnopqrstuvwxyz')


def validate_domains(text):
    for domain in text.splitlines():
        msg = "Invalid domain name: '%(domain)s'." % {'domain': domain}
        validators.DomainValidator(message=msg)(domain)


def validate_dict(value):
    if not isinstance(value, dict):
        raise ValidationError("Value is not a 'dictionary' type.")


class CastingManager(managers.InheritanceManager):
    """
    Manager that automatically downcasts instances to their inherited types.
    """

    def get_queryset(self):
        return super().get_queryset().select_subclasses()


class Task(models.Model):
    """
    Base class for models that represent a self-contained process/task. The
    actor function should return no value and accept the Task instance's primary
    key as its only argument. Any configuration should be provided through
    related database models.

    The task's status transitions are handled by `mortar.middleware.TaskStatus`,
    and the transition methods should not be invoked directly.

    The public API consists of `send`ing the task, or composing as a `message`
    in a Dramatiq `pipeline`. Additionally, the actor may self-terminate by
    raising `Task.Abort`.

        >>> task = MyTask.objects.create()
        >>> task.send()
        ...
        >>> task.refresh_from_db()
        >>> task.status
        'running'
        ...
        >>> task.refresh_from_db()
        >>> task.status
        'done'

    """
    STATUS = Choices(
        ('not_queued', 'Not queued'),
        ('enqueued', 'Waiting'),
        ('running', 'Running'),
        ('done', 'Finished'),
        ('failed', 'Failed'),

        # non-standard state
        ('aborted', 'Stopped'),
    )

    message_id = models.UUIDField(null=True, default=None, editable=False,
                                  help_text="Dramatiq message ID")
    status = FSMField(choices=STATUS, default=STATUS.not_queued, editable=False)
    started_at = models.DateTimeField(null=True, editable=False)
    finished_at = models.DateTimeField(null=True, editable=False)

    objects = managers.InheritanceManager()
    downcast = CastingManager()

    class Meta:
        base_manager_name = 'downcast'

    class Abort(Exception):
        pass

    @property
    def runtime(self):
        try:
            return self.finished_at - self.started_at
        except TypeError:
            return None

    @property
    def task_path(self):
        """
        The module path of the task function. This property must be implemented.
        """
        raise NotImplementedError

    @cached_property
    def task(self):
        return import_string(self.task_path)

    def message(self, **options):
        """
        Create a message for composition in a pipeline or group.
        """
        if self.message_id:
            raise RuntimeError('Task already queued.')

        # pipe_ignore arg prevents results from being passed along the pipeline.
        # tasks must be self contained and return no result.
        options['pipe_ignore'] = True
        return self.task.message_with_options(
            kwargs={'task_id': self.pk},
            **options
        )

    def send(self, **options):
        """
        Send a message to the broker for processing.
        """
        if self.message_id:
            raise RuntimeError('Task already queued.')

        return self.task.send_with_options(
            kwargs={'task_id': self.pk},
            **options
        )

    def revoke(self):
        """
        Signal a task to self-abort. This feature is not provided by default,
        and it is necessary to implement a method by which the the Task subclass
        signals to the task function to raise `Task.Abort`.
        """
        raise NotImplementedError

    @transition(field=status, source=STATUS.not_queued, target=STATUS.enqueued)
    def _enqueue(self, message_id):
        assert self.message_id is None

        self.message_id = message_id

    @transition(field=status, source=STATUS.enqueued, target=STATUS.running)
    def _start(self):
        self.started_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.done)
    def _finish(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.failed)
    def _fail(self):
        self.finished_at = timezone.now()

    @transition(field=status, source=STATUS.running, target=STATUS.aborted)
    def _abort(self):
        self.finished_at = timezone.now()

    def log_error(self, error):
        return self.errors.create(message=error)

    def log_exception(self, exc):
        # Note: first argument is ignored since python 3.5
        traceback = ''.join(format_exception(None, exc, exc.__traceback__))
        return self.errors.create(message=str(exc), traceback=traceback)

    def clear_errors(self):
        self.errors.delete()


class TaskError(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='errors')
    timestamp = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    traceback = models.TextField()

    class Meta:
        ordering = ('-timestamp', )

    def __str__(self):
        return "Task Error: {}".format(self.message)


class Crawler(models.Model):
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    start_urls = models.TextField(help_text="List of URLs to crawl (separated by newlines).")
    allowed_domains = models.TextField(blank=True, validators=[validate_domains],
                                       help_text="List of domains to allow (separated by newlines).")
    blocked_domains = models.TextField(blank=True, validators=[validate_domains],
                                       help_text="List of domains to block (separated by newlines).")
    config = jsonfield.JSONField(blank=True, default=dict, validators=[validate_dict],
                                 help_text="Override settings for Scrapy.")

    def __str__(self):
        return 'Crawler: %s' % self.pk

    def start(self, **options):
        if self.task.status != self.task.STATUS.not_queued:
            raise RuntimeError('Crawler has already been started.')

        self.task.send(**options)

    def stop(self):
        if self.task.status != self.task.STATUS.running:
            raise RuntimeError('Crawler is not currently running.')
        self.task.revoke()

    def restart(self, **options):
        """
        Restart the crawler by clearing its existing state. The index is not
        cleared, and will contain updated, duplicate responses.
        """
        if self.task.status == self.task.STATUS.running:
            raise RuntimeError('Crawler is already running.')

        if os.path.exists(self.state_dir):
            shutil.rmtree(self.state_dir)

        self.task.delete()
        self.task = CrawlerTask.objects.create(crawler=self)
        self.task.send(**options)

    def resume(self, **options):
        """
        Resume the crawler from where it left off. It is assumed the
        state directory was not cleared by the user.
        """
        if self.task.status == self.task.STATUS.running:
            raise RuntimeError('Crawler is already running.')

        if not self.resumable:
            raise RuntimeError('Crawler is not resumable (missing metadata).')

        self.task.delete()
        self.task = CrawlerTask.objects.create(crawler=self)
        self.task.send(**options)

    @property
    def resumable(self):
        return os.path.exists(self.state_dir)

    @property
    def state_dir(self):
        """
        Directory where crawler state/persistence data is stored.
        """
        return utils.path(f'.crawlers/{self.uuid}')

    @property
    def index_name(self):
        return b36_uuid.encode(self.uuid)

    @cached_property
    def index(self):
        return Index(self.index_name)

    @property
    def documents(self):
        return documents.Document.context(index=self.index_name)

    @staticmethod
    def _create_index(sender, instance, created, **kwargs):
        if created:
            documents.Document.init(instance.index_name)

    @staticmethod
    def _delete_index(sender, instance, **kwargs):
        try:
            instance.index.delete()
        except TransportError:
            pass


post_save.connect(Crawler._create_index, sender=Crawler)
post_delete.connect(Crawler._delete_index, sender=Crawler)


class CrawlerTask(Task):
    crawler = models.OneToOneField(Crawler, on_delete=models.CASCADE, related_name='task')
    revoked = models.BooleanField(default=False, editable=False,
                                  help_text="Task has been marked for revocation.")

    @property
    def task_path(self):
        return 'mortar.tasks.crawl'

    def revoke(self):
        self.revoked = True
        self.save(update_fields=['revoked'])


@receiver(post_save, sender=Crawler)
def crawler_task(sender, instance, created, **kwargs):
    if created:
        CrawlerTask.objects.create(crawler=instance)


class SentenceTokenizer(models.Model):
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    crawler = models.OneToOneField(Crawler, on_delete=models.CASCADE)

    @classmethod
    def to_sentences(cls, document):
        # see: https://github.com/nltk/nltk/issues/947
        from nltk.tokenize import sent_tokenize

        sentences = sent_tokenize(document.text)
        sentences = [
            documents.Sentence(
                document_id=document.meta.id,
                text=sentence,
            ) for sentence in sentences
        ]
        return sentences

    def tokenize(self, document):
        if self.sentences.search() \
                         .filter('term', document_id=document.meta.id) \
                         .count() > 0:
            return  # noop - already tokenized

        sentences = self.to_sentences(document)
        self.sentences.bulk_create(sentences)

    @property
    def index_name(self):
        return b36_uuid.encode(self.uuid)

    @cached_property
    def index(self):
        return Index(self.index_name)

    @property
    def documents(self):
        return self.crawler.documents

    @property
    def sentences(self):
        return documents.Sentence.context(index=self.index_name)

    @staticmethod
    def _create_index(sender, instance, created, **kwargs):
        if created:
            documents.Sentence.init(instance.index_name)

    @staticmethod
    def _delete_index(sender, instance, **kwargs):
        try:
            instance.index.delete()
        except TransportError:
            pass


post_save.connect(SentenceTokenizer._create_index, sender=SentenceTokenizer)
post_delete.connect(SentenceTokenizer._delete_index, sender=SentenceTokenizer)


class Annotation(models.Model):
    crawler = models.ForeignKey(Crawler, on_delete=models.CASCADE)
    query = models.TextField(help_text="Elasticsearch query JSON.")

    def execute(self):
        if self.document_set.exists() or self.sentence_set.exists():
            return  # noop - already executed

        query = json.loads(self.query)
        tokenizer = self.crawler.sentencetokenizer
        sentences = [s for s in tokenizer.sentences.search().update_from_dict(query).scan()]
        documents = tokenizer.documents.mget({s.document_id for s in sentences}, missing='skip')

        documents = [Document(
            elastic_id=doc.meta.id,
            annotation=self,
            url=doc.url,
            timestamp=doc.timestamp,
            text=doc.text,
        ) for doc in documents]
        Document.objects.bulk_create(documents)

        sentences = [Sentence(
            elastic_id=sentence.meta.id,
            annotation=self,
            document=Document.objects.get(elastic_id=sentence.document_id),
            text=sentence.text,
        ) for sentence in sentences]
        Sentence.objects.bulk_create(sentences)

    class Meta:
        ordering = ['pk']


class Document(models.Model):
    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE)
    elastic_id = models.CharField(max_length=20)
    url = models.URLField(max_length=2083)
    timestamp = models.DateTimeField()
    text = models.TextField()


class Sentence(models.Model):
    annotation = models.ForeignKey(Annotation, on_delete=models.CASCADE)
    elastic_id = models.CharField(max_length=20)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    text = models.TextField()
