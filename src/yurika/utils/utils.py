import os
import sys
from contextlib import contextmanager
from io import StringIO
from logging import getLogger

from django.conf import settings


__all__ = [
    'path', 'capture_output', 'log_level', 'humanize_timedelta',
]


def path(value):
    """
    Builds absolute paths relative to settings.BASE_DIR.
    """
    return os.path.abspath(os.path.join(settings.BASE_DIR, value))


@contextmanager
def capture_output():
    """
    Temporarily capture stdout/stderr streams.
    """
    tmpout, tmperr = StringIO(), StringIO()
    stdout, stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = tmpout, tmperr
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = stdout, stderr


@contextmanager
def log_level(logger, level):
    """
    Temporarily override a logger's log level.
    """
    if isinstance(logger, str):
        logger = getLogger(logger)

    actual = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(actual)


def humanize_timedelta(td):
    """
    Convert a timedelta into a textual representation.

    ex::

        >>> humanize_timedelta(timedelta(seconds=1234))
        '20 minutes, 34 seconds'
        >>> humanize_timedelta(timedelta(days=2, seconds=14))
        '2 days, 14 seconds'

    """
    if td is None:
        return

    parts, seconds = {}, td.total_seconds()
    parts['days'], seconds = divmod(seconds, 24 * 60 * 60)
    parts['hours'], seconds = divmod(seconds, 60 * 60)
    parts['minutes'], seconds = divmod(seconds, 60)
    parts['seconds'] = seconds

    return ', '.join([
        f'{int(value)} {name}'
        for name, value in parts.items()
        if value > 0
    ])
