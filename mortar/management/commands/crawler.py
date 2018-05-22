import json
import uuid
from argparse import ArgumentTypeError

import elasticsearch
import progressbar
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.utils.formats import localize
from django.utils.termcolors import colorize
from terminaltables import SingleTable

from mortar import models
from project import utils

from .utils import side_by_side, style_by_line, truncate_message


RESTART_HELP = """
Clear a crawler's persistent state and restart it.
Note that this does not clear the Elasticsearch index and will result in
updated, duplicate documents.
"""

RESUME_HELP = """
Resume a crawler from where it left off.
"""


validate_url = URLValidator(schemes=['http', 'https'])


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


def nth_error(value):
    value = int(value)

    if value > 0:
        return value - 1

    raise ArgumentTypeError(f"errors are 1-indexed")


def file_contents(filename):
    try:
        with open(filename, 'r') as file:
            return file.read()
    except OSError:
        raise ArgumentTypeError(f"can't open '{filename}'")


def urls(filename):
    contents = file_contents(filename)

    urls = []
    try:
        for url in contents.strip().split('\n'):
            url = url.strip()
            validate_url(url)
            urls.append(url)

    except ValidationError:
        raise ArgumentTypeError(f"invalid URL '{url}' in '{filename}'")

    return urls


def domains(filename):
    contents = file_contents(filename)

    domains = []
    for domain in contents.strip().split('\n'):
        domain = domain.strip()
        domains.append(domain)

        pre = f"invalid domain '{domain}' in '{filename}'"

        # simple domain validation
        if '//' in domain:
            raise ArgumentTypeError(f"{pre} - domain must not contain a scheme")

        if '/' in domain:
            raise ArgumentTypeError(f"{pre} - domain must not contain a path")

    return domains


def config(filename):
    contents = file_contents(filename)

    try:
        return json.loads(contents)
    except json.JSONDecodeError as e:
        raise ArgumentTypeError(str(e))


class Command(BaseCommand):
    help = "Crawler task management"

    def add_arguments(self, parser):
        # https://github.com/python/cpython/pull/3027
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        # #################################################################### #
        # #### INFO ########################################################## #
        parser = subparsers.add_parser('info', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.", nargs='?')

        # #################################################################### #
        # #### CREATE ######################################################## #
        parser = subparsers.add_parser('create', cmd=self)
        parser.add_argument('-s', '--start-urls', dest='start', type=urls, required=True,
                            help="File path of URLs to start crawling from, delimited by newlines.")
        parser.add_argument('-c', '--config', dest='config', type=config,
                            help="File path for a Scrapy JSON config.")
        parser.add_argument('--no-tokenize', action='store_false', dest='tokenize', default=True,
                            help="Don't tokenize crawled documents into sentences.")

        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('-a', '--allowed-domains', dest='allow', type=domains,
                           help="File path of domains to allow, delimited by newlines.")
        group.add_argument('-b', '--blocked-domains', dest='block', type=domains,
                           help="File path of domains to block, delimited by newlines.")

        # #################################################################### #
        # #### CONFIG ######################################################## #
        parser = subparsers.add_parser('config', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--get-value', dest='get', metavar='NAME', help="Get a config value.")
        group.add_argument('--set-value', dest='set', metavar=('NAME', 'VALUE'), nargs=2, help="Set a config value.")
        group.add_argument('--unset-value', dest='unset', metavar='NAME', help="Unset a config value.")
        group.add_argument('--replace', dest='replace', metavar='FILENAME', type=config, help="Replace the config.")
        group.add_argument('--echo', dest='echo', action='store_true', default=False, help="View the config.")

        # #################################################################### #
        # #### DELETE ######################################################## #
        parser = subparsers.add_parser('delete', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")

        # #################################################################### #
        # #### START ######################################################### #
        parser = subparsers.add_parser('start', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        # #################################################################### #
        # #### STOP ########################################################## #
        parser = subparsers.add_parser('stop', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")

        # #################################################################### #
        # #### RESTART ####################################################### #
        parser = subparsers.add_parser('restart', cmd=self, help=RESTART_HELP)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        # #################################################################### #
        # #### RESUME ######################################################## #
        parser = subparsers.add_parser('resume', cmd=self, help=RESUME_HELP)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        # #################################################################### #
        # #### ERRORS ######################################################## #
        parser = subparsers.add_parser('errors', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('error', type=nth_error, help="Nth error.", nargs='?')

        # #################################################################### #
        # #### TOKENIZE ###################################################### #
        parser = subparsers.add_parser('tokenize', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('--stats', action='store_true', dest='stats', default=False,
                            help="Display the tokenized sentence statistics.")

        # #################################################################### #
        # #### STATS ######################################################### #
        parser = subparsers.add_parser('stats', cmd=self)

    def handle(self, command, **options):
        handler = getattr(self, command)

        try:
            return handler(**options)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

    def style_status(self, status, text):
        STATUS = models.CrawlerTask.STATUS
        style_func = {
            STATUS.running: self.style.WARNING,
            STATUS.failed: self.style.NOTICE,
        }.get(status, lambda _: _)

        return style_func(text)

    def document_count(self, crawler):
        try:
            return crawler.documents.search().count()
        except elasticsearch.TransportError:
            return 'err!'

    def header(self):
        return [
            'ID',
            'Elasticsearch index',
            'Status',
            'Resumable',
            'docs',
            'errs',
            'Crawler started',
            'Crawler stopped',
            'Runtime',
        ]

    def row(self, crawler):
        return [
            crawler.pk,
            colorize(crawler.index_name, fg='cyan'),
            self.style_status(crawler.task.status, crawler.task.get_status_display()),
            'Yes' if crawler.resumable else 'No',
            self.document_count(crawler),
            crawler.task.errors.count(),
            localize(crawler.task.started_at) or '-',
            localize(crawler.task.finished_at) or '-',
            utils.humanize_timedelta(crawler.task.runtime) or '-',
        ]

    def task_options(self, options):
        task_options = {}
        if options.get('time_limit') is not None:
            # convert to milliseconds
            task_options['time_limit'] = options['time_limit'] * 1000

        return task_options

    def info(self, crawler=None, **options):
        if crawler is not None:
            return self.instance_info(crawler, **options)

        crawlers = models.Crawler.objects.all()

        data = [self.row(crawler) for crawler in crawlers]
        data.insert(0, self.header())

        table = SingleTable(data, title='Crawlers: ' + str(crawlers.count()))
        table.justify_columns[0] = 'right'
        self.stdout.write(table.table)

    def instance_info(self, crawler, **options):
        instance = SingleTable([self.header(), self.row(crawler)])
        instance.justify_columns[0] = 'right'

        start = SingleTable([[u] for u in crawler.start_urls.split('\n')], title=' Start URLs ')
        allow = SingleTable([[d] for d in crawler.allowed_domains.split('\n')], title=' Allowed ')
        block = SingleTable([[d] for d in crawler.blocked_domains.split('\n')], title=' Blocked ')
        start.inner_heading_row_border = False
        block.inner_heading_row_border = False

        self.stdout.write(instance.table)
        self.stdout.write('')
        output = start.table
        if crawler.allowed_domains:
            output = side_by_side(output, allow.table)
        if crawler.blocked_domains:
            output = side_by_side(output, block.table)
        self.stdout.write(output)
        self.stdout.write('')

    def stats(self, **options):
        crawlers = models.Crawler.objects.all()
        data = [
            (display, crawlers.filter(task__status=name).count())
            for name, display
            in models.CrawlerTask.STATUS
        ]
        data.insert(0, ('Total', crawlers.count()))

        self.stdout.write(SingleTable(data, title='Crawlers').table)

    def create(self, start, allow, block, config, tokenize, **options):
        self.stdout.write('Creating ...')

        start = '\n'.join(start)
        allow = '\n'.join(allow) if allow is not None else ''
        block = '\n'.join(block) if block is not None else ''

        c = models.Crawler.objects.create(
            start_urls=start,
            allowed_domains=allow,
            blocked_domains=block,
            config=config,
        )

        if tokenize:
            models.SentenceTokenizer.objects.create(crawler=c)
        self.stdout.write(self.style.SUCCESS(f'ID: {c.uuid}'))

    def config(self, crawler, **options):
        if options.get('get') is not None:
            name = options['get']
            if name in crawler.config:
                value = json.dumps(crawler.config.get(name))
            else:
                value = '<not set>'

            self.stdout.write('GET %s: %s' % (name, value))

        elif options.get('set') is not None:
            name, value = options['set']
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ArgumentTypeError('must be valid JSON')

            crawler.config[name] = value
            crawler.save(update_fields=['config'])
            self.stdout.write('SET %s: %s' % (name, value))

        elif options.get('unset') is not None:
            name = options['unset']
            if name in crawler.config:
                value = json.dumps(crawler.config.get(name))
            else:
                value = '<not set>'

            del crawler.config[name]
            crawler.save(update_fields=['config'])
            self.stdout.write('UNSET %s: %s' % (name, value))

        elif options.get('replace') is not None:
            contents = options['replace']

            crawler.config = contents
            crawler.save(update_fields=['config'])
            self.stdout.write('Replaced config')

        elif options.get('echo'):
            self.stdout.write(json.dumps(crawler.config, indent=4, sort_keys=True))

    def delete(self, crawler, **options):
        self.stdout.write('Deleting ...')
        crawler.delete()

    def start(self, crawler, **options):
        self.stdout.write('Starting ...')
        crawler.start(**self.task_options(options))

    def stop(self, crawler, **options):
        self.stdout.write('Stopping ...')
        crawler.stop()

    def restart(self, crawler, **options):
        self.stdout.write('Restarting ...')
        crawler.restart(**self.task_options(options))

    def resume(self, crawler, **options):
        self.stdout.write('Resuming ...')
        crawler.resume(**self.task_options(options))

    def errors(self, crawler, error=None, **options):
        errors = crawler.task.errors.all()

        if not errors.exists():
            self.stdout.write('No errors.')
            return

        # error detail
        if error is not None:
            return self.instance_error(errors[error])

        # error list
        tz = errors[0].timestamp.strftime('%Z')
        HEADER = ['n', f'Timestamp ({tz})', 'Message']
        data = [
            [i, error.timestamp.strftime('%Y-%m-%d %H:%M:%S'), '']
            for i, error in enumerate(errors, start=1)
        ]
        data.insert(0, HEADER)

        table = SingleTable(data, title='Errors: ' + str(errors.count()))
        table.justify_columns[0] = 'right'

        # truncate error messages to max column width.
        max_width = table.column_max_width(2)

        # first row contains headers
        for row, error in zip(table.table_data[1:], errors):
            row[2] = truncate_message(error.message, max_width)

        self.stdout.write(table.table)

    def instance_error(self, error):
        data = [
            ['Timestamp', error.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')],
            ['Message', style_by_line(error.message, self.style.NOTICE)],
        ]

        if error.traceback:
            data.append(
                ['Traceback', style_by_line(error.traceback, self.style.NOTICE)]
            )

        table = SingleTable(data)
        table.inner_row_border = True
        table.justify_columns[0] = 'right'

        self.stdout.write(table.table)

    def tokenize(self, crawler, stats, **options):
        tokenizer = getattr(crawler, 'sentencetokenizer', None)
        if tokenizer is None:
            tokenizer = models.SentenceTokenizer.objects.create(crawler=crawler)

        if stats:
            return self.tokenizer_stats(tokenizer)

        self.stdout.write('Tokenizing documents into sentences ...')
        documents = crawler.documents.search()
        for doc in progressbar.progressbar(documents.scan(), max_value=documents.count()):
            tokenizer.tokenize(doc)

    def tokenizer_stats(self, tokenizer):
        def chunk(iterable, n):
            for i in range(0, len(iterable), n):
                yield iterable[i:i + n]

        document_ids = [hit.meta.id for hit in tokenizer.documents.search()[:100]]
        sentence_counts = [
            tokenizer.sentences.search().filter('term', document_id=doc).count()
            for doc in document_ids
        ]

        data = [
            ['%s | %s' % pair for pair in zip(l, r)]
            for l, r in zip(chunk(document_ids, 5), chunk(sentence_counts, 5))
        ]

        table = SingleTable(data, title=' Documents: %d | Sentences: %d ' % (
            tokenizer.documents.search().count(),
            tokenizer.sentences.search().count(),
        ))
        table.inner_heading_row_border = False

        self.stdout.write(table.table)
