import json
import uuid
from argparse import ArgumentTypeError

from django.core.management.base import BaseCommand, CommandError
from django.utils.termcolors import colorize
from elasticsearch_dsl import Search, exceptions
from terminaltables import SingleTable

from yurika.mortar import models


def crawler(value):
    try:
        return models.Crawler.objects.get(pk=value)
    except models.Crawler.DoesNotExist:
        pass

    try:
        return models.Crawler.objects.get(uuid=uuid.UUID(value))
    except (ValueError, models.Crawler.DoesNotExist):
        pass

    raise ArgumentTypeError(f"invalid ID or UUID '{value}'")


def annotation(value):
    try:
        return models.Annotation.objects.get(pk=value)
    except models.Annotation.DoesNotExist:
        raise ArgumentTypeError(f"invalid ID '{value}'")


def file_contents(filename):
    try:
        with open(filename, 'r') as file:
            return file.read()
    except OSError:
        raise ArgumentTypeError(f"can't open '{filename}'")


def query(filename):
    contents = file_contents(filename)

    try:
        Search.from_dict(json.loads(contents))
    except json.JSONDecodeError:
        raise ArgumentTypeError(f"invalid JSON in '{filename}'")
    except exceptions.ElasticsearchDslException as e:
        raise ArgumentTypeError(str(e))

    return contents


class Command(BaseCommand):
    help = "Annotation management"

    def add_arguments(self, parser):
        # https://github.com/python/cpython/pull/3027
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        # #################################################################### #
        # #### INFO ########################################################## #
        parser = subparsers.add_parser('info', cmd=self)

        # #################################################################### #
        # #### CREATE ######################################################## #
        parser = subparsers.add_parser('create', cmd=self)
        parser.add_argument('-c', '--crawler', dest='crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('-q', '--query', dest='query', type=query, required=True,
                            help="JSON file containing the Elasticsearch query.")

        # #################################################################### #
        # #### DELETE ######################################################## #
        parser = subparsers.add_parser('delete', cmd=self)
        parser.add_argument('annotation', type=annotation, help="Annotation ID.")

    def handle(self, command, **options):
        handler = getattr(self, command)

        try:
            return handler(**options)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

    def info(self, **options):
        annotations = models.Annotation.objects.all()

        data = [[
            colorize(annotation.pk, fg='cyan'),
            annotation.document_set.count(),
            annotation.sentence_set.count()
        ] for annotation in annotations]
        data.insert(0, ['ID', 'Documents', 'Sentences'])

        table = SingleTable(data, title='Annotations: ' + str(annotations.count()))
        table.justify_columns[0] = 'right'

        self.stdout.write(table.table)

    def create(self, crawler, query, **options):
        self.stdout.write('Creating ... ', ending='')

        models.Annotation.objects \
            .create(crawler=crawler, query=query) \
            .execute()

        self.stdout.write(self.style.SUCCESS('Done!'))

    def delete(self, annotation, **options):
        self.stdout.write('Deleting ... ', ending='')
        annotation.delete()
        self.stdout.write(self.style.SUCCESS('Done!'))
