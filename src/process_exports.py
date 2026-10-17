
import re
from pathlib import Path
import json


from .tokenize_js.tokenize import process as tokenize_js




def detect_module_type(module):
    return Path(module.path).suffix


def make_template(name,source,return_statements):
    return f'''
const {name} = (function() {{

{source}

{return_statements}

}}());

'''


class ProcessExportsError(Exception):
    """Raised when exports processing fails."""

    def __init__(self, msg, *args, **kwargs):
        super().__init__(f"Error processing exports: {msg}", *args, **kwargs)


def _skip_while(tokens, index, predicate):
    """Advance ``index`` while ``predicate(token)`` holds."""
    while index < len(tokens) and predicate(tokens[index]):
        index += 1
    return index


def _skip_insignificant(tokens, index, *, include_newlines=True):
    """Skip whitespace, comments, and (optionally) newlines."""
    kinds = ('SPACE', 'NEWLINE', 'COMMENT') if include_newlines else ('SPACE', 'COMMENT')
    return _skip_while(tokens, index, lambda token: token.kind in kinds)


def _declaration_keyword_index(tokens, index):
    """Return the declaration keyword index, advancing ``async`` to ``function``.

    ``index`` points at ``async`` / ``function`` / ``class`` / ``const`` /
    ``var`` / ``let``.  Returns None if ``async`` is not followed by ``function``.
    """
    if tokens[index].value == 'async':
        index = _skip_insignificant(tokens, index + 1)
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
    name_index = _skip_insignificant(tokens, index)
    if name_index < len(tokens) and tokens[name_index].value == '*':
        star_index = name_index
        name_index = _skip_insignificant(tokens, name_index + 1)
    return name_index, star_index


def _statement_end(tokens, index):
    """Return the index just past the statement terminator after ``index``.

    Skips horizontal whitespace and comments, then returns the index just past
    the ``;`` or newline, or ``len(tokens)`` at end of input, or None if the
    statement is not properly terminated.
    """
    index = _skip_insignificant(tokens, index, include_newlines=False)
    if index >= len(tokens):
        return index
    if tokens[index].kind in ('SEMICOLON', 'NEWLINE'):
        return index + 1
    return None

def process_js(module, config):

    class ProcessModuleError(ProcessExportsError):
        """Raised when exports processing fails."""

        def __init__(self, msg, *args, **kwargs):
            super().__init__(f'{msg}: in module "{module.path}"', *args, **kwargs)

    module_name = module.name
    source = module.source

    named_exports = []
    default_exports = []
    explicit_exports = []

    source_updated = ''
    tokens = tokenize_js(source)
    index_current = 0
    while index_current < len(tokens):
        token = tokens[index_current]
        if not (token.kind == 'IDENT' and token.value == 'export'):
            source_updated += token.value
            index_current += 1
            continue

        # We are at an ``export`` statement; skip the ``export`` keyword.
        i = _skip_insignificant(tokens, index_current + 1)
        if i >= len(tokens):
            raise ProcessModuleError('Unexpected end of string after "export"')

        if tokens[i].value == 'default':
            i = _skip_insignificant(tokens, i + 1)
            if i >= len(tokens):
                raise ProcessModuleError('Unexpected end of string after "export"')

            if tokens[i].value in ('function', 'class', 'async'):
                # ``export default [async] function|class [*] name|()|{}``
                first_keyword_index = i  # ``async`` / ``function`` / ``class``
                keyword_index = _declaration_keyword_index(tokens, i)
                if keyword_index is None:
                    raise ProcessModuleError('Unexpected end of string: expected "function" after "async"')
                name_index, star_index = _declaration_name_index(tokens, keyword_index + 1)
                if name_index >= len(tokens):
                    raise ProcessModuleError('Unexpected end of string after "export"')

                name = tokens[name_index]
                if name.kind == 'IDENT':
                    default_exports.append(name.value)
                    # Keep the declaration; drop only ``export default``.
                    index_current = first_keyword_index
                elif name.kind in ('LPAREN', 'LBRACE'):
                    # Anonymous default function/class (optionally a generator):
                    # synthesize a name so the declaration stays valid once
                    # ``export default`` is stripped.
                    default_name = '_default'
                    default_exports.append(default_name)
                    source_updated += ''.join(
                        tokens[k].value for k in range(first_keyword_index, keyword_index + 1)
                    ) + ('*' if star_index is not None else '') + ' ' + default_name
                    index_current = (star_index + 1) if star_index is not None else (keyword_index + 1)
                else:
                    raise ProcessModuleError(f'export... default... function/class/... and then expected an identifier, got "{name.value}"')
                continue

            # ``export default <identifier|number>;``
            name = tokens[i]
            if name.kind not in ('IDENT', 'NUMBER'):
                raise ProcessModuleError(f'export... default... and then expected an identifier, got "{name.value}" ({name.kind})')
            default_exports.append(name.value)
            statement_end = _statement_end(tokens, i + 1)
            if statement_end is None:
                raise ProcessModuleError(f'export default IDENT, and then expected EOD, newline, or semicolon, got "{name.value}"')
            index_current = statement_end
            continue
        if tokens[i].value == '{':
            # ``export { ... };``
            exports = []
            index_spec_body_start = _skip_insignificant(tokens, i + 1)
            index_spec_end = _skip_while(tokens, index_spec_body_start, lambda token: token.value != '}')
            index_spec_body_end = index_spec_end - 1
            spec = ''
            for k in range(index_spec_body_start, index_spec_body_end + 1):
                if tokens[k].kind != 'COMMENT':
                    spec += tokens[k].value
            spec_parts = [s.strip() for s in spec.split(',')]
            for spec_part in spec_parts:
                spec_name, spec_alias = None, None
                matches = re.match(r'^\s*(\w+)\s+as\s+(\w+)\s*$', spec_part)
                if matches:
                    spec_name = matches[1]
                    spec_alias = matches[2]
                else:
                    matches = re.match(r'^\s*(\w+)\s*$', spec_part)
                    if matches:
                        spec_name = matches[1]
                        spec_alias = None
                    else:
                        raise ProcessModuleError(f'Unexpected syntax within export {{ ... }} : "{spec}"')
                if not spec_alias:
                    exports.append(spec_name)
                else:
                    exports.append(f'{spec_alias}: {spec_name}')
            statement_end = _statement_end(tokens, index_spec_end + 1)
            if statement_end is None:
                raise ProcessModuleError('export { ... }, and then expected EOD, newline, or semicolon')
            index_current = statement_end
            explicit_exports.append(exports)
            continue

        if tokens[i].value in ('async', 'function', 'const', 'var', 'let', 'class'):
            # ``export [async] function|class|const|var|let name``
            keyword_index = _declaration_keyword_index(tokens, i)
            if keyword_index is None:
                raise ProcessModuleError('Unexpected end of string: expected "function" after "async"')
            name_index, _star_index = _declaration_name_index(tokens, keyword_index + 1)
            if name_index >= len(tokens):
                raise ProcessModuleError('Unexpected end of string after "export"')
            name = tokens[name_index]
            if name.kind != 'IDENT':
                raise ProcessModuleError(f'export... function/let/const/var/class/... and then expected an identifier, got "{name.value}"')
            named_exports.append(name.value)
            # Keep the declaration; drop only the ``export`` keyword.
            index_current = i
            continue

        raise ProcessModuleError(f'Unexpected symbol follows "export" statement: "{tokens[i].value}"')

    if len(default_exports) > 1:
        raise ProcessModuleError('Multiple default exports')

    if len(explicit_exports) > 0 and (len(named_exports) > 0):
        raise ProcessModuleError('Named/default exports, and explicit export')

    if len(explicit_exports) > 1:
        raise ProcessModuleError('Multiple explicit exports in file')

    if len(explicit_exports) > 0:
        named_exports = explicit_exports[0]

    return_statements = 'return {\n' + ''.join([f'    {name},\n' for name in named_exports]) + '' + (f'    default: {default_exports[0]},\n' if len(default_exports) > 0 else '') + '};'

    return make_template(module_name, source_updated, return_statements)


def process_css(module, config):
    scripts = f"""
var style = document.createElement('style');
style.textContent = {json.dumps(module.source)};
document.head.appendChild(style);
"""
    return_statements = '\nreturn style;\n';
    return make_template(module.name,scripts,return_statements)

def process_vue(module, config):
    raise ProcessModuleError(f'Can\'t handle extension "{module_type}": not implemented')


def process(module, config):

    class ProcessModuleError(ProcessExportsError):
        """Raised when exports processing fails."""

        def __init__(self, msg, *args, **kwargs):
            super().__init__(f'{msg}: in module "{module.path}"', *args, **kwargs)

    module_name = module.name
    source = module.source
    module_type = detect_module_type(module)

    if module_type=='.js' or (module_type=='' and f'{module.path}'.startswith('global:')):
        return process_js(module, config)
    elif module_type=='.css':
        return process_css(module, config)
    elif module_type=='.vue':
        return process_vue(module, config)
    else:
        raise ProcessModuleError(f'Can\'t handle extension "{module_type}": not implemented')
