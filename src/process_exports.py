

from pathlib import Path
import json


from .tokenize_js.tokenize import process as tokenize_js
from .parse_export import ExportParseError, parse_export_statement




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


def process_js(module, config):

    class ProcessModuleError(ProcessExportsError):
        """Raised when exports processing fails."""

        def __init__(self, msg, *args, **kwargs):
            super().__init__(f'{msg}: in module "{module.path}"', *args, **kwargs)

    tokens = tokenize_js(module.source)

    named_exports = []
    default_exports = []
    explicit_exports = []

    source_updated = ''
    index_current = 0
    while index_current < len(tokens):
        token = tokens[index_current]
        if not (token.kind == 'IDENT' and token.value == 'export'):
            source_updated += token.value
            index_current += 1
            continue

        try:
            statement = parse_export_statement(tokens, index_current)
        except ExportParseError as e:
            raise ProcessModuleError(str(e))

        if statement.kind == 'named':
            named_exports.extend(statement.names)
        elif statement.kind == 'default':
            default_exports.extend(statement.names)
        else:  # 'explicit'
            explicit_exports.append(statement.names)

        source_updated += statement.prefix
        index_current = statement.resume_index

    if len(default_exports) > 1:
        raise ProcessModuleError('Multiple default exports')

    if len(explicit_exports) > 0 and (len(named_exports) > 0):
        raise ProcessModuleError('Named/default exports, and explicit export')

    if len(explicit_exports) > 1:
        raise ProcessModuleError('Multiple explicit exports in file')

    if len(explicit_exports) > 0:
        named_exports = explicit_exports[0]

    return_statements = 'return {\n' + ''.join([f'    {name},\n' for name in named_exports]) + '' + (f'    default: {default_exports[0]},\n' if len(default_exports) > 0 else '') + '};'

    return make_template(module.name, source_updated, return_statements)


def process_css(module, config):
    scripts = f"""
var style = document.createElement('style');
style.textContent = {json.dumps(module.source)};
document.head.appendChild(style);
"""
    return_statements = '\nreturn style;\n';
    return make_template(module.name,scripts,return_statements)

def process_vue(module, config):
    raise ProcessExportsError('Can\'t handle extension ".vue": not implemented')


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
