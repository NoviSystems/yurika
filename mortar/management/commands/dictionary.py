import logging
from argparse import ArgumentTypeError

import elasticsearch
from django.core.management.base import BaseCommand, CommandError
from django.utils.termcolors import colorize
from elasticsearch_dsl import Index

# UnixTable uses VT-100 escape sequences, which gives incorrect string lengths
# WindowsTable is compatible
from terminaltables.other_tables import WindowsTable as SingleTable

from mortar import documents
from project.utils import log_level
from .utils import truncate_message


def file_contents(filename):
    try:
        with open(filename, 'r') as file:
            return file.read()
    except OSError:
        raise ArgumentTypeError(f"can't open '{filename}'")


def dictionary(id):
    try:
        with log_level('elasticsearch', logging.ERROR):
            return documents.Dictionary.get(id=id)
    except elasticsearch.exceptions.NotFoundError:
        raise ArgumentTypeError('does not exist')


def terms(filename):
    contents = file_contents(filename)
    return contents.split()


class Command(BaseCommand):
    help = "Dictionary management"

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
        parser.add_argument('-n', '--name', dest='name', type=str, required=True,
                            help="Human-friendly name.")
        parser.add_argument('-t', '--terms', dest='terms', type=terms, required=True,
                            help="File path containing the terms (whitespace delimited.")

        # #################################################################### #
        # #### DELETE ######################################################## #
        parser = subparsers.add_parser('delete', cmd=self)
        parser.add_argument('dictionary', type=dictionary, help="Dictionary ID.")

    def handle(self, command, **options):
        handler = getattr(self, command)

        try:
            return handler(**options)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

    def info(self, dictionary=None, **options):
        dictionaries = documents.Dictionary.search()

        data = [[colorize(d.meta.id, fg='cyan'), d.name, ''] for d in dictionaries]
        data.insert(0, ['Elasticsearch ID', 'Name', 'Terms'])

        table = SingleTable(data, title='Dictionaries: ' + str(dictionaries.count()))

        max_width = table.column_max_width(2)

        # first row contains headers
        for row, dictionary in zip(table.table_data[1:], dictionaries):
            row[2] = truncate_message(', '.join(dictionary.terms), max_width)

        self.stdout.write(table.table)

    def create(self, name, terms, **options):
        self.stdout.write('Creating ... ', ending='')

        if not Index('dictionaries').exists():
            documents.Dictionary.init()

        d = documents.Dictionary(name=name, terms=terms)
        d.save()

        self.stdout.write(self.style.SUCCESS('Done!\n'))
        self.stdout.write(self.style.SUCCESS(f'ID: {d.meta.id}'))

    def delete(self, dictionary, **options):
        self.stdout.write('Deleting ... ', ending='')
        dictionary.delete()
        self.stdout.write(self.style.SUCCESS('Done!'))
