import re


vt100_re = re.compile(r'(\x1b\(0(.*?)\x1b\(B)', flags=re.IGNORECASE)


def vt100_strip(line):
    """
    Strip the line of the VT100 escape sequences that switch to the special
    graphics set. This is useful for getting actual length of the line.

    ex:

        >>> line = '\x1b(0l\x1b(B Title \x1b(0qqqqqqqqqqk\x1b(B'
        >>> print(line)
        ┌ Title ──────────┐
        >>> print(vt100_strip(line))
        l Title qqqqqqqqqqk

    """
    # outer group matches the enclosing escape sequences
    # inner group matches the set of inner drawing chars
    for outer, inner in vt100_re.findall(line):
        line = line.replace(outer, inner, 1)
    return line


def side_by_side(left, right, spacer=8):
    """
    Format two blocks of text to display side-by-side.

    It is assumed that each block of text is consistent in width.
    """
    left = left.splitlines()
    right = right.splitlines()

    # total number of lines
    lines = max(len(left), len(right))
    spacers = [' ' * spacer] * lines

    # add blank lines to left side
    blank = ' ' * len(vt100_strip(left[0]))
    left.extend([blank] * (lines - len(left)))

    # add blank lines to right side
    blank = ' ' * len(vt100_strip(right[0]))
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
