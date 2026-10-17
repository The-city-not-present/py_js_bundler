"""Parsing of ES module ``export`` statements.

Parallel to :mod:`parse_import`: ``process_exports`` no longer walks tokens by
hand to understand an ``export`` statement — it calls
:func:`parse_export_statement` and then just rewrites based on the structured
result.

New export forms (re-exports, expression defaults, ...) should be added here by
introducing a new :attr:`ExportStatement.kind` and populating its fields, rather
than growing more token-walking code in ``process_exports``.
"""

import re
from dataclasses import dataclass

from .helper_token_utils import skip_insignificant, skip_while, statement_end


class ExportParseError(Exception):
    """Raised when an ``export`` statement cannot be parsed."""


@dataclass(frozen=True)
class ExportStatement:
    # One of 'named' (``export [async] function|class|const|var|let name``),
    # 'default' (``export default ...``) or 'explicit' (``export { ... }``).
    kind: str
    # Exported keys, in order.  For 'default' this is a one-element tuple
    # holding the default value (``('aaa',)``, ``('42',)`` or ``('_default',)``).
    names: tuple[str, ...]
    # Token index where the caller loop should resume copying source.
    resume_index: int
    # Text to emit before resuming.  Only anonymous default exports need it
    # (a name has to be synthesized); empty otherwise.
    prefix: str = ''


def _declaration_keyword_index(tokens, index):
    """Return the declaration keyword index, advancing ``async`` to ``function``.

    ``index`` points at ``async`` / ``function`` / ``class`` / ``const`` /
    ``var`` / ``let``.  Returns None if ``async`` is not followed by ``function``.
    """
    if tokens[index].value == 'async':
        index = skip_insignificant(tokens, index + 1)
        if index < len(tokens) and tokens[index].value == 'function':
            return index
        return None
    return index


def _declaration_name_index(tokens, index):
    """Return ``(name_index, star_index)`` from just after a declaration keyword.

    ``name_index`` points at the declared name (an IDENT) or at the ``(`` /
    ``{`` that begins an anonymous function/class.  ``star_index`` points at an
    optional generator ``*`` (or None).
    """
    star_index = None
    name_index = skip_insignificant(tokens, index)
    if name_index < len(tokens) and tokens[name_index].value == '*':
        star_index = name_index
        name_index = skip_insignificant(tokens, name_index + 1)
    return name_index, star_index


def parse_export_statement(tokens, start):
    """Parse the export statement beginning at ``tokens[start]``.

    ``start`` must point at an ``export`` identifier token.
    """
    i = skip_insignificant(tokens, start + 1)
    if i >= len(tokens):
        raise ExportParseError('Unexpected end of string after "export"')

    if tokens[i].value == 'default':
        return _parse_default_export(tokens, i)
    if tokens[i].value == '{':
        return _parse_explicit_export(tokens, i)
    if tokens[i].value in ('async', 'function', 'const', 'var', 'let', 'class'):
        return _parse_named_export(tokens, i)

    raise ExportParseError(f'Unexpected symbol follows "export" statement: "{tokens[i].value}"')


def _parse_named_export(tokens, i):
    # ``i`` points at ``async`` / ``function`` / ``const`` / ``var`` / ``let`` / ``class``.
    keyword_index = _declaration_keyword_index(tokens, i)
    if keyword_index is None:
        raise ExportParseError('Unexpected end of string: expected "function" after "async"')
    name_index, _star_index = _declaration_name_index(tokens, keyword_index + 1)
    if name_index >= len(tokens):
        raise ExportParseError('Unexpected end of string after "export"')
    name = tokens[name_index]
    if name.kind != 'IDENT':
        raise ExportParseError(f'export... function/let/const/var/class/... and then expected an identifier, got "{name.value}"')
    # The caller drops the ``export`` keyword and keeps the declaration.
    return ExportStatement(kind='named', names=(name.value,), resume_index=i)


def _parse_default_export(tokens, i):
    # ``i`` points at ``default``.
    j = skip_insignificant(tokens, i + 1)
    if j >= len(tokens):
        raise ExportParseError('Unexpected end of string after "export"')

    if tokens[j].value in ('function', 'class', 'async'):
        # ``export default [async] function|class [*] name|()|{}``
        first_keyword_index = j
        keyword_index = _declaration_keyword_index(tokens, j)
        if keyword_index is None:
            raise ExportParseError('Unexpected end of string: expected "function" after "async"')
        name_index, star_index = _declaration_name_index(tokens, keyword_index + 1)
        if name_index >= len(tokens):
            raise ExportParseError('Unexpected end of string after "export"')

        name = tokens[name_index]
        if name.kind == 'IDENT':
            return ExportStatement(kind='default', names=(name.value,), resume_index=first_keyword_index)
        if name.kind in ('LPAREN', 'LBRACE'):
            # Anonymous default function/class (optionally a generator).
            prefix = ''.join(
                tokens[k].value for k in range(first_keyword_index, keyword_index + 1)
            ) + ('*' if star_index is not None else '') + ' _default'
            resume_index = (star_index + 1) if star_index is not None else (keyword_index + 1)
            return ExportStatement(kind='default', names=('_default',), resume_index=resume_index, prefix=prefix)
        raise ExportParseError(f'export... default... function/class/... and then expected an identifier, got "{name.value}"')

    # ``export default <identifier|number>;``
    name = tokens[j]
    if name.kind not in ('IDENT', 'NUMBER'):
        raise ExportParseError(f'export... default... and then expected an identifier, got "{name.value}" ({name.kind})')
    end = statement_end(tokens, j + 1)
    if end is None:
        raise ExportParseError(f'export default IDENT, and then expected EOD, newline, or semicolon, got "{name.value}"')
    return ExportStatement(kind='default', names=(name.value,), resume_index=end)


def _parse_explicit_export(tokens, i):
    # ``i`` points at ``{``.
    names = []
    body_start = skip_insignificant(tokens, i + 1)
    end = skip_while(tokens, body_start, lambda token: token.value != '}')
    body_end = end - 1
    spec = ''
    for k in range(body_start, body_end + 1):
        if tokens[k].kind != 'COMMENT':
            spec += tokens[k].value
    for spec_part in (s.strip() for s in spec.split(',')):
        name, alias = None, None
        matches = re.match(r'^\s*(\w+)\s+as\s+(\w+)\s*$', spec_part)
        if matches:
            name = matches[1]
            alias = matches[2]
        else:
            matches = re.match(r'^\s*(\w+)\s*$', spec_part)
            if matches:
                name = matches[1]
                alias = None
            else:
                raise ExportParseError(f'Unexpected syntax within export {{ ... }} : "{spec}"')
        names.append(f'{alias}: {name}' if alias else name)
    end = statement_end(tokens, end + 1)
    if end is None:
        raise ExportParseError('export { ... }, and then expected EOD, newline, or semicolon')
    return ExportStatement(kind='explicit', names=tuple(names), resume_index=end)

