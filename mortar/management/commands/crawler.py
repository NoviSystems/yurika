import time
import uuid
from argparse import ArgumentTypeError

import elasticsearch
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.formats import localize
from django.utils.termcolors import colorize

# UnixTable uses VT-100 escape sequences, which gives incorrect string lengths
# WindowsTable is compatible
from terminaltables.other_tables import WindowsTable as SingleTable

from mortar import models
from project import utils

RESTART_HELP = """
Clear a crawler's persistent state and restart it.
Note that this does not clear the Elasticsearch index and will result in
updated, duplicate documents.
"""

RESUME_HELP = """
Resume a crawler from where it left off.
"""

BOUNCE_HELP = """
Safely stop a crawler then resume from where it left off.
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

        pre = f"invalid domain '{domain}' in '{filename} "

        # validate domain
        if '//' in domain:
            raise ArgumentTypeError(f"{pre} - domain must not contain a scheme")

        if '/' in domain:
            raise ArgumentTypeError(f"{pre} - domain must not contain a path")

    return domains


def side_by_side(left, right, spacer=8):
    """
    Format two blocks of text to display side-by-side.

    It is assumed that each block of text is consistent in width.
    """
    left = left.split('\n')
    right = right.split('\n')

    # total number of lines
    lines = max(len(left), len(right))
    spacers = [' ' * spacer] * lines

    # add blank lines to left side
    blank = ' ' * len(left[0])
    left.extend([blank] * (lines - len(left)))

    # add blank lines to right side
    blank = ' ' * len(right[0])
    right.extend([blank] * (lines - len(right)))

    return '\n'.join([''.join(parts) for parts in zip(left, spacers, right)])


def style_by_line(text, style_func):
    return '\n'.join([style_func(line) for line in text.splitlines()])


def truncate_message(message, max_width):
    # truncate extra lines to single line + ellipsis
    lines = message.splitlines()
    message = lines[0] + '...' if len(lines) > 1 else lines[0]

    # truncate to width + ellipsis
    if len(message) > max_width:
        message = message[:max_width - 3] + '...'

    return message


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
        parser.add_argument('-c', '--crawl', dest='crawl', type=urls, required=True,
                            help="File path of URLs to crawl, delimited by newlines.")
        parser.add_argument('-b', '--block', dest='block', type=domains,
                            help="File path of domains to block, delimited by newlines.")
        parser.add_argument('--no-tokenize', action='store_false', dest='tokenize', default=True,
                            help="Don't tokenize crawled documents into sentences.")

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
        # #### BOUNCE ######################################################## #
        parser = subparsers.add_parser('bounce', cmd=self, help=BOUNCE_HELP)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('--wait', dest='wait', type=int, default=0,
                            help="How many seconds to wait before resuming the task.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        # #################################################################### #
        # #### ERRORS ######################################################## #
        parser = subparsers.add_parser('errors', cmd=self)
        parser.add_argument('crawler', type=crawler, help="Crawler ID or UUID.")
        parser.add_argument('error', type=nth_error, help="Nth error.", nargs='?')

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

        crawl = SingleTable([[u] for u in crawler.urls.split('\n')], title=' Crawl URLs ')
        block = SingleTable([[d] for d in crawler.block.split('\n')], title=' Block URLs ')
        crawl.inner_heading_row_border = False
        block.inner_heading_row_border = False

        self.stdout.write(instance.table)
        self.stdout.write('')
        self.stdout.write(side_by_side(crawl.table, block.table))
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

    def create(self, crawl, block, tokenize, **options):
        self.stdout.write('Creating ...')

        crawl = '\n'.join(crawl)
        block = '\n'.join(block) if block is not None else ''

        c = models.Crawler.objects.create(urls=crawl, block=block)
        if tokenize:
            models.SentenceTokenizer.objects.create(crawler=c)
        self.stdout.write(self.style.SUCCESS(f'ID: {c.uuid}'))

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

    def bounce(self, crawler, wait, **options):
        self.stop(crawler, **options)

        while crawler.task.status == crawler.task.STATUS.running:
            crawler.task.refresh_from_db()
            time.sleep(.1)

        # wait to resume (defaults to 0 seconds)
        time.sleep(wait)

        self.resume(crawler, **options)

    def errors(self, crawler, error=None, **options):
        errors = crawler.task.errors.all()

        # error detail
        if error is not None:
            return self.instance_error(errors[error])

        if not errors.exists():
            self.stdout.write('No errors.')

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
