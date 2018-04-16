import time
import uuid
from argparse import ArgumentTypeError

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.formats import localize
from django.utils.termcolors import colorize

# UnixTable uses VT-100 escape sequences, which gives incorrect string lengths
# WindowsTable is compatible
from terminaltables.other_tables import WindowsTable as SingleTable

from mortar import models

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


def urls_file(filename):
    try:
        with open(filename, 'r') as file:
            contents = file.read()
    except OSError as e:
        raise ArgumentTypeError(f"can't open '{filename}'")

    urls = []
    try:
        for url in contents.strip().split('\n'):
            url = url.strip()
            validate_url(url)
            urls.append(url)

    except ValidationError as e:
        raise ArgumentTypeError(f"invalid URL '{url}' in '{filename}'")

    return urls


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


class Command(BaseCommand):
    help = "Crawler task management"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command')

        parser = subparsers.add_parser('info', cmd=self)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.", nargs='?')

        parser = subparsers.add_parser('create', cmd=self)
        parser.add_argument('-c', '--crawl', dest='crawl', type=urls_file, required=True,
                            help="File path of URLs to crawl, delimited by newlines.")
        parser.add_argument('-b', '--block', dest='block', type=urls_file,
                            help="File path of URLs to block, delimited by newlines.")

        parser = subparsers.add_parser('start', cmd=self)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        parser = subparsers.add_parser('stop', cmd=self)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.")

        parser = subparsers.add_parser('restart', cmd=self, help=RESTART_HELP)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        parser = subparsers.add_parser('resume', cmd=self, help=RESUME_HELP)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        parser = subparsers.add_parser('bounce', cmd=self, help=BOUNCE_HELP)
        parser.add_argument('id', type=uuid.UUID, help="Crawler UUID.")
        parser.add_argument('--wait', dest='wait', type=int, default=0,
                            help="How many seconds to wait before resuming the task.")
        parser.add_argument('--time-limit', dest='time_limit', type=int,
                            help="Time limit (in seconds) for how long the "
                                 "crawler should run before it is terminated.")

        parser = subparsers.add_parser('stats', cmd=self)

    def handle(self, command, **options):
        handler = getattr(self, command)

        return handler(**options)

    def style_status(self, status, text):
        STATUS = models.CrawlerTask.STATUS
        style_func = {
            STATUS.running: self.style.WARNING,
            STATUS.failed: self.style.NOTICE,
        }.get(status, lambda _: _)

        return style_func(text)

    def row(self, i, crawler):
        return [
            i,
            colorize(crawler.uuid, fg='cyan'),
            self.style_status(crawler.task.status, crawler.task.get_status_display()),
            crawler.documents.count(),
            crawler.task.errors.count(),
            localize(crawler.task.started_at) or '-',
            localize(crawler.task.finished_at) or '-',
        ]

    def info(self, id=None, **options):
        if id is not None:
            return self.instance_info(id, **options)

        crawlers = models.Crawler.objects.all()

        HEADER = ['', 'ID', 'Status', 'docs', 'errs', 'Crawler started', 'Crawler stopped']
        data = [self.row(i, c) for i, c in enumerate(crawlers, 1)]
        data.insert(0, HEADER)

        table = SingleTable(data, title='Crawlers: ' + str(crawlers.count()))
        self.stdout.write(table.table)

    def instance_info(self, id, **options):
        crawler = models.Crawler.objects.get(uuid=id)

        instance = SingleTable([
            ['ID', 'Status', 'docs', 'errs', 'Crawler started', 'Crawler stopped'],
            self.row(0, crawler)[1:]
        ])

        crawl = SingleTable([[u] for u in crawler.urls.split('\n')], title=' Crawl URLs ')
        block = SingleTable([[' ' * 20]], title=' Block URLs ')
        # block = SingleTable(crawler.block.split('\n'), title=' Block URLs ')
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

    def create(self, crawl, **options):
        self.stdout.write('Creating ...')

        c = models.Crawler.objects.create(urls='\n'.join(crawl))
        self.stdout.write(self.style.SUCCESS(f'ID: {c.uuid}'))

    def start(self, id, **options):
        self.stdout.write('Starting ...')

        message_opts = {}
        if options.get('time_limit') is not None:
            # convert to milliseconds
            message_opts['time_limit'] = options['time_limit'] * 1000

        crawler = models.Crawler.objects.get(uuid=id)
        crawler.task.send(**message_opts)

    def stop(self, id, **options):
        self.stdout.write('Stopping ...')

        crawler = models.Crawler.objects.get(uuid=id)
        crawler.task.revoke()

    def restart(self, id, **options):
        self.stdout.write('Restarting ...')

        message_opts = {}
        if options.get('time_limit') is not None:
            # convert to milliseconds
            message_opts['time_limit'] = options['time_limit'] * 1000

        crawler = models.Crawler.objects.get(uuid=id)
        crawler.restart()
        crawler.task.send(**message_opts)

    def resume(self, id, **options):
        self.stdout.write('Resuming ...')

        message_opts = {}
        if options.get('time_limit') is not None:
            # convert to milliseconds
            message_opts['time_limit'] = options['time_limit'] * 1000

        crawler = models.Crawler.objects.get(uuid=id)
        crawler.resume()
        crawler.task.send(**message_opts)

    def bounce(self, id, wait, **options):
        self.stop(id, **options)

        crawler = models.Crawler.objects.get(uuid=id)
        while crawler.task.status == crawler.task.STATUS.running:
            crawler.task.refresh_from_db()
            time.sleep(.1)

        # wait to resume (defaults to 0 seconds)
        time.sleep(wait)

        self.resume(id, **options)
