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
