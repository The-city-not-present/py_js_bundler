"""Parsing of ES module ``import`` statements.

Discovery and import-rewriting both need to understand ``import`` statements,
so that logic lives here in one place.

* :func:`parse_import_statement` parses a single statement starting at an
  ``import`` token and returns an :class:`ImportStatement`.  It returns ``None``
  for valid constructs that only *look* like imports (dynamic ``import(...)``
  and ``import.meta``) and raises :class:`ImportParseError` for malformed input.
* :func:`extract_import_specifiers` is a convenience wrapper that returns the
  module specifiers of every top-level ``import`` in a source string.
"""

from dataclasses import dataclass

from .tokenize_js.tokenize import process as tokenize_js


class ImportParseError(Exception):
    """Raised when an ``import`` statement cannot be parsed."""


@dataclass(frozen=True)
class ImportStatement:
    start: int            # token index of the ``import`` keyword
    end: int              # token index just past the end of the statement
    specifier: str        # module specifier, e.g. ``./lib``
    side_effect: bool     # True for ``import './lib';``
    bindings: str | None  # binding clause text for binding imports, else None


def _skip_ws(tokens, index):
    """Skip SPACE / NEWLINE / COMMENT tokens."""
    while index < len(tokens) and tokens[index].kind in ('SPACE', 'NEWLINE', 'COMMENT'):
        index += 1
    return index


def _unquote(value):
    quote = value[0]
    assert quote in ("'", '"', "`")
    assert value[-1] == quote
    return value[1:-1].replace('\\' + quote, quote)


def _find_from(tokens, index):
    """Return the index of the ``from`` keyword of a binding import, or None.

    ``from`` is also a valid binding/alias name (``import { from } from 'x'``),
    so only an identifier followed by a string literal qualifies as the keyword.
    """
    n = len(tokens)
    while index < n:
        token = tokens[index]
        if token.kind == 'SEMICOLON':
            return None
        if token.kind == 'IDENT' and token.value == 'from':
            after = _skip_ws(tokens, index + 1)
            if after < n and tokens[after].kind == 'STRING':
                return index
        index += 1
    return None


def _statement_end(tokens, string_index):
    """Return the index just past the terminator following a specifier string."""
    index = string_index + 1
    while index < len(tokens) and tokens[index].kind == 'SPACE':
        index += 1
    if index >= len(tokens):
        return index
    if tokens[index].kind in ('SEMICOLON', 'NEWLINE'):
        return index + 1
    raise ImportParseError('expected ";" or newline after import statement')


def parse_import_statement(tokens, start):
    """Parse the import statement beginning at ``tokens[start]``.

    ``start`` must point at an ``import`` identifier token.  Returns
    :class:`ImportStatement` for a static import, ``None`` for dynamic
    ``import(...)`` / ``import.meta``, and raises :class:`ImportParseError` for
    malformed input.
    """
    n = len(tokens)
    after_import = _skip_ws(tokens, start + 1)
    if after_import >= n:
        raise ImportParseError('unexpected end of input after "import"')

    first = tokens[after_import]

    if first.kind == 'STRING':
        # import './lib';
        specifier = _unquote(first.value)
        end = _statement_end(tokens, after_import)
        return ImportStatement(
            start=start,
            end=end,
            specifier=specifier,
            side_effect=True,
            bindings=None,
        )

    if first.kind in ('LPAREN', 'DOT'):
        # import('./lib') — dynamic import, or import.meta — not static imports.
        return None

    # import ... from './lib';
    from_index = _find_from(tokens, after_import)
    if from_index is None:
        raise ImportParseError('expected "from" in import statement')
    specifier_index = _skip_ws(tokens, from_index + 1)
    if specifier_index >= n or tokens[specifier_index].kind != 'STRING':
        raise ImportParseError('expected module specifier string after "from"')

    bindings = ''.join(token.value for token in tokens[after_import:from_index])
    specifier = _unquote(tokens[specifier_index].value)
    end = _statement_end(tokens, specifier_index)
    return ImportStatement(
        start=start,
        end=end,
        specifier=specifier,
        side_effect=False,
        bindings=bindings,
    )


def extract_import_specifiers(source):
    """Return the module specifiers of all top-level ``import`` statements."""
    tokens = tokenize_js(source)
    specifiers = []
    i = 0
    n = len(tokens)
    while i < n:
        token = tokens[i]
        if token.kind == 'IDENT' and token.value == 'import':
            statement = parse_import_statement(tokens, i)
            if statement is not None:
                specifiers.append(statement.specifier)
                i = statement.end
                continue
        i += 1
    return specifiers
