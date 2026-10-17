"""Shared low-level token helpers for the ES module parsers.

Both :mod:`parse_import` and :mod:`parse_export` walk token lists to locate
statement boundaries; these helpers keep that logic in one place.
"""


def skip_while(tokens, index, predicate):
    """Advance ``index`` while ``predicate(token)`` holds."""
    while index < len(tokens) and predicate(tokens[index]):
        index += 1
    return index


def skip_insignificant(tokens, index, *, include_newlines=True):
    """Skip whitespace, comments, and (optionally) newlines."""
    kinds = ('SPACE', 'NEWLINE', 'COMMENT') if include_newlines else ('SPACE', 'COMMENT')
    return skip_while(tokens, index, lambda token: token.kind in kinds)


def statement_end(tokens, index):
    """Return the index just past the statement terminator after ``index``.

    Skips horizontal whitespace and comments, then returns the index just past
    the ``;`` or newline, or ``len(tokens)`` at end of input, or None if the
    statement is not properly terminated.
    """
    index = skip_insignificant(tokens, index, include_newlines=False)
    if index >= len(tokens):
        return index
    if tokens[index].kind in ('SEMICOLON', 'NEWLINE'):
        return index + 1
    return None


def unquote(value):
    """Strip the surrounding quotes of a string/template token value."""
    quote = value[0]
    assert quote in ("'", '"', "`")
    assert value[-1] == quote
    return value[1:-1].replace('\\' + quote, quote)
