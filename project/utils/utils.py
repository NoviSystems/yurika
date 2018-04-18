import os

from django.conf import settings


def path(value):
    """
    Builds absolute paths relative to settings.BASE_DIR.
    """
    return os.path.abspath(os.path.join(settings.BASE_DIR, value))


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
