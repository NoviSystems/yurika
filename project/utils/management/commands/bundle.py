# -*- coding: utf-8 -*-

import os
import re
import sys
from contextlib import contextmanager
from subprocess import (
    PIPE, CalledProcessError, Popen, check_call, check_output,
)
from tempfile import mkdtemp

from django.core.management.base import BaseCommand, CommandError


class StepFail(BaseException):
    """
    Exception class to signal to the "step" context manager that execution
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
            '-t', '--tar', default=False, dest='tar', action='store_true',
            help='Write output as a tar file (uses a zip archive otherwise).',
        )
        parser.add_argument(
            'branch',
            help='Git ref to bundle, e.g. a branch or commit hash.',
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.rows, self.cols = self.get_terminal_size()
        self.sep = '    ' + (u'═' * (self.cols - 8))

    def get_terminal_size(self):
        process = Popen(['stty', 'size'], stdout=PIPE)
        out, _ = process.communicate()
        return [int(v) for v in out.split()]

    def check_uncommitted(self):
        try:
            check_call(['git', 'diff-index', '--quiet', 'HEAD', '--'])
        except CalledProcessError:
            raise CommandError("There are uncommitted changes. Stash or "
                               "commit them before proceeding.")

    @contextmanager
    def step(self, msg='', success='done', failure='fail'):
        self.stderr.write(f'  - {msg} ', ending='')
        try:
            yield
        except Exception:
            self.stderr.write(self.style.ERROR(failure))
            raise
        except StepFail as e:
            self.stderr.write(self.style.ERROR(str(e)))
            sys.exit(1)
        self.stderr.write(self.style.SUCCESS(success))

    def stream(self, args, cwd=None, check=True):
        """
        Stream the output of the subprocess
        """
        sys.stderr.write("\x1b7")  # Save cursor pos
        sys.stderr.write("\x1b[?1047h")  # Set alternate screen
        sys.stderr.flush()
        try:
            process = Popen(args, cwd=cwd)
            process.wait()

            if check and process.returncode != 0:
                raise CalledProcessError(process.returncode, args)
        finally:
            sys.stderr.write("\x1b[?1047l")  # Reset to regular screen
            sys.stderr.write("\x1b8")  # Restore cursor pos
            sys.stderr.flush()

    def handle(self, *args, **options):
        self.check_uncommitted()

        ref = options['branch']
        sha = check_output(['git', 'rev-parse', ref]).decode('ASCII').strip()
        ext = 'tar' if options['tar'] else 'zip'

        tmp = mkdtemp()  # build directory
        out = options['output']  # output path

        # default output path
        if not out:
            out = f'bundles/build-{ref}-{sha[:8]}.{ext}'

        # Both zip and tar accept `-` to mean standard out
        if out != '-':
            out = os.path.abspath(out)

        # ensure output directory
        check_call(['mkdir', '-p', os.path.dirname(out)])

        msg = f'Creating application bundle for: {ref}'
        self.stderr.write(self.style.MIGRATE_HEADING(msg))

        # copy the project to archive directory
        with self.step('Creating build directory at {} ...'.format(tmp)):
            archive = Popen(['git',  'archive', ref], stdout=PIPE)
            check_call(['tar', '-x', '-C', tmp], stdin=archive.stdout)
            archive.stdout.close()
            archive.wait()
            if archive.returncode > 0:
                raise CommandError(f"'{ref}' is an invalid git reference")

        # create version file
        with self.step('Creating version file {} ...'.format(sha)):
            with open(os.path.join(tmp, 'version'), 'w') as versionfile:
                versionfile.write(f'{sha}\n')

        # javascript build
        if os.path.exists(os.path.join(tmp, 'package.json')):
            with self.step('Found \'package.json\'. Building javascript...'):
                try:
                    self.stream(['npm', 'install', '--only=production'], cwd=tmp)
                    self.stream(['npm', 'run', 'build'], cwd=tmp)
                except OSError as e:
                    raise StepFail("Could not execute NPM commands.\nIf you "
                                   "don't need to build javascript bundles, "
                                   "remove the package.json from "
                                   "the repository.\nOriginal "
                                   "exception was: {}".format(e)) from e
        else:
            self.stderr.write('  - No \'package.json\' found. Skipping javascript build.')

        # Create zip archive
        with self.step('Writing bundle...'):
            if options['tar']:
                self.stream(['tar', 'cvf', out, '.'], cwd=tmp)
            else:
                self.stream(['zip', '-r', out, '.'], cwd=tmp)
        self.stderr.write('')

        if os.path.exists('.elasticbeanstalk/config.yml'):
            with self.step('Updating eb config...'):
                with open('.elasticbeanstalk/config.yml') as config:
                    text = config.read()
                with open('.elasticbeanstalk/config.yml', 'w') as config:
                    config.write(re.sub(r'bundles/.*.zip', out, text))

        # write paths to stderr
        if not out.startswith(tmp):
            self.stderr.write('Build directory:')
            self.stderr.write(self.style.NOTICE(f'  {tmp}'))
        self.stderr.write('Bundle path:')
        self.stderr.write(self.style.NOTICE(f'  {out}'))
