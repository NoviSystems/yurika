from collections import OrderedDict

from django import template


register = template.Library()

GRID_COLUMNS = 12


def parse_sizes(sizes):
    """
    >>> parse_sizes('md-6 xs-8')
    {'md': 6, 'xs': 8}
    """
    return OrderedDict(
        pair.rsplit('-', 1)
        for pair in sizes.split()
    )


@register.filter
def cols(sizes):
    """
    Converts string pairs of column sizes into a css class string.

        >>> inputcols('md-6 xs-8'})
        'col-md-6 col-xs-8'
    """
    return ' '.join([
        'col-{}-{}'.format(k, v)
        for k, v in parse_sizes(sizes).items()
    ])


@register.filter
def inversecols(sizes):
    """
    Converts string pairs of columns sizes into a css class string, but
    calculates the inverse size based on the number of columns in the grid.

        >>> inputcols('md-6 xs-8'})
        'col-md-6 col-xs-4'
    """
    return ' '.join([
        'col-{}-{}'.format(k, GRID_COLUMNS - int(v))
        for k, v in parse_sizes(sizes).items()
    ])


@register.filter
def template(boundfield):
    form = boundfield.form

    return form.get_template(boundfield)
