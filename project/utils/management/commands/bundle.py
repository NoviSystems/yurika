# -*- coding: utf-8 -*-

import os
import sys
from contextlib import contextmanager
from subprocess import check_call, Popen, PIPE, CalledProcessError

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

DATETIME_FORMAT = '%Y%m%d_%H%M%S'

class StepFail(BaseException):
    """Exception class to signal to the "step" context manager that execution
    has failed, but not to dump a traceback

    """

class Command(BaseCommand):
    help = 'Build/bundle the application for deployment to production.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output', default=None, dest='output',
            help='Specifies file to which the output is written.'
        )
        parser.add_argument(
            '-r', '--git-reference', default='master', dest='ref',
            help='Git reference to bundle, e.g. a branch or commit hash.',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.rows, self.cols = self.get_terminal_size()
        self.sep = '    %s' % (u'═' * (self.cols - 8))

    def get_terminal_size(self):
        process = Popen(['stty', 'size'], stdout=PIPE)
        out, _ = process.communicate()
        return [int(v) for v in out.split()]

    @contextmanager
    def step(self, msg='', success='done', failure='fail'):
        self.stdout.write('  - %s ' % (msg,), ending='')
        try:
            yield
        except Exception:
            self.stdout.write(self.style.ERROR(failure))
            raise
        except StepFail as e:
            self.stdout.write(self.style.ERROR(str(e)))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS(success))

    def stream(self, args, cwd=None, check=True):
        """
        Stream the output of the subprocess
        """
        sys.stdout.write("\x1b7") # Save cursor pos
        sys.stdout.write("\x1b[?1047h") # Set alternate screen
        sys.stdout.flush()
        try:
            process = Popen(args, cwd=cwd)
            process.wait()

            if check and process.returncode != 0:
                raise CalledProcessError(process.returncode, args)
        finally:
            sys.stdout.write("\x1b[?1047l") # Reset to regular screen
            sys.stdout.write("\x1b8") # Restore cursor pos
            sys.stdout.flush()

    def handle(self, *args, **options):
        ref = options['ref']
        ts = now().strftime(DATETIME_FORMAT)
        path = 'bundles/build-%(ref)s-%(ts)s' % locals()
        out = options['output'] or (path + '.zip')

        msg = 'Creating application bundle for: %s' % ref
        self.stdout.write(self.style.MIGRATE_HEADING(msg))

        # copy the project to archive directory
        with self.step('Creating build directory at {} ...'.format(path)):
            archive = Popen(['git',  'archive', ref], stdout=PIPE)
            check_call(['mkdir', '-p', path])
            check_call(['tar', '-x', '-C', path], stdin=archive.stdout)
            archive.stdout.close()
            archive.wait()
            if archive.returncode > 0:
                raise CommandError("'%s' is an invalid git reference" % ref)

        # javascript build
        if os.path.exists(os.path.join(path, 'package.json')):
            with self.step('Found \'package.json\'. Building javascript...'):
                try:
                    self.stream(['npm', 'install', '--only=production'], cwd=path)
                    self.stream(['npm', 'run', 'build'], cwd=path)
                except OSError as e:
                    raise StepFail("Could not execute NPM commands.\nIf you "
                                   "don't need to build javascript bundles, "
                                   "remove the package.json from "
                                   "the repository.\nOriginal "
                                   "exception was: {}".format(e)) from e
        else:
            self.stdout.write('  - No \'package.json\' found. Skipping javascript build.')

        # Create zip archive
        with self.step('Writing bundle...'):
            self.stream(['zip', '-r', os.path.abspath(out), '.'], cwd=path)
        self.stdout.write('')

        # write paths to stdout
        if not out.startswith(path):
            self.stdout.write('Build directory:')
            self.stdout.write(self.style.NOTICE('  %s' % path))
        self.stdout.write('Bundle path:')
        self.stdout.write(self.style.NOTICE('  %s' % out))
