
import re

from .common_defs import resolve_import
from .tokenize_js.tokenize import process as tokenize_js
from .parse_import import ImportParseError, parse_import_statement
from .log import logger
from .helper_classify_spec_type import (
    classify_module_specifier,
    # ModuleSpecifierType,
    classify_module_specifier_role_for_bundler,
    ModuleSpecifierBundlerRole,
    resolve_aliases,
)
# classify_module_specifier_role_for_bundler(name, base, module.path, aliases)
# resolve_aliases(name, base, current_module_path, aliases)




class ProcessImportsError(Exception):
    """Raised when imports processing fails."""

    def __init__(self, msg, *args, **kwargs):
        super().__init__(f"Error processing imports: {msg}", *args, **kwargs)



def process(module,modules_dicts,config):

    if not config:
        config = dict()

    aliases = config.get('aliases',{})
    project_root = config.get('project_root',None)

    class ProcessModuleError(ProcessImportsError):
        """Raised when imports processing fails."""

        def __init__(self, msg, *args, **kwargs):
            super().__init__(f'{msg}: in module "{module.path}"', *args, **kwargs)

    source = module.source

    source_updated = ''
    global_imports = {}

    tokens = tokenize_js(source)
    index_current = 0
    while index_current<len(tokens):
        token = tokens[index_current]

        if token.kind=='IDENT' and token.value=='import':
            try:
                import_statement = parse_import_statement(tokens, index_current)
            except ImportParseError as e:
                raise ProcessModuleError(str(e))

            if import_statement is None:
                # Dynamic import('./x') / import.meta — leave untouched.
                source_updated += token.value
                index_current += 1
                continue

            name = import_statement.specifier
            if classify_module_specifier_role_for_bundler(name, project_root, module.path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                import_module_path = resolve_import('global://',name)
            else:
                import_module_path = resolve_import(module.path,resolve_aliases(name, project_root, module.path, aliases))
            imported_module = modules_dicts.get(import_module_path)
            if not imported_module:
                raise ProcessModuleError(f'Failed to resolve import: path = "{name}", resolved path = "{import_module_path}", type = "{classify_module_specifier(name)}". module object == "{imported_module}"')

            if import_statement.side_effect:
                source_updated += '\n' + imported_module.name + ';\n\n'
                index_current = import_statement.end
                continue

            specs = import_statement.bindings
            index_current = import_statement.end

            if re.match(r'^\s*(\w+)\s*$',specs):
                # import somethingA from './somewhere';
                matches = re.match(r'^\s*(\w+)\s*$',specs)
                default_name = matches[1]
                source_updated += '\n' + f'const {default_name} = {imported_module.name}.default;\n' + ';\n\n'
            elif re.match(r'\s*\{\s*([^\n]*?)\s*\}\s*$',specs):
                # import { somethingA, somethingB } from './somewhere';
                matches = re.match(r'\s*(\{\s*[^\n]*?\s*\})\s*$',specs)
                specs_named = matches[1]
                source_updated += '\n' + f'const {specs_named} = {imported_module.name};' + '\n'
            elif re.match(r'\s*(\w+(?:\s+\bas\b\s*\b\w+)?)\s*,\s*\{\s*([^\n]*?)\s*\}\s*$',specs):
                # import somethingA, { somethingB, somethingC } from './somewhere';
                matches = re.match(r'\s*(\w+(?:\s+\bas\b\s*\b\w+)?)\s*,\s*(\{\s*[^\n]*?\s*\})\s*$',specs)
                specs_default = matches[1]
                specs_named = matches[2]
                if specs_default:
                    default_name = None
                    specs_default_alias = None
                    if re.match(r'^\s*(\w+)\s*\bas\b\s*(\w+)\s*$',specs_default):
                        matches = re.match(r'^\s*(\w+)\s*\bas\b\s*(\w+)\s*$',specs_default)
                        default_name = matches[1]
                        specs_default_alias = matches[2]
                    else:
                        matches = re.match(r'^\s*(\w+)\s*$',specs_default)
                        assert not not matches
                        default_name = matches[1]
                        specs_default_alias = None
                    source_updated += '\n' + f'const {specs_default_alias if specs_default_alias else default_name} = {imported_module.name}.default;\n' + ';\n\n'
                source_updated += '\n' + f'const {specs_named} = {imported_module.name};' + '\n'
            else:
                raise ProcessModuleError(f'Error parsing imports statement: expected "import \'./somewhere\'", or "import {{ somethingA, somethingB }} from \'./somewhere\'", or "import somethingA from \'./somewhere\'", or "import somethingA, {{ somethingB, somethingC }} from \'./somewhere\'", but got "import" that does not match any of those: "{specs}"') # assert

            source_updated += '\n'
            continue

        else:
            source_updated += token.value

        index_current += 1

    # TODO: how is that, "combine_imports" is undefined, but it is working? Highlighted by linter... But is working
    # maybe current design does not imply that something appears in global_imports dict, maybe it's alyaws emty, and that inner part is never called...
    global_imports = { name: combine_imports(statements) for name,statements in global_imports.items() }
    logger.debug('[DEBUG-imports]: (%s) global imports captured (raw): %r', module.path, global_imports)
    logger.debug('[DEBUG-imports]: (%s) global imports captured, globally: %s', module.path, ', '.join(global_imports.keys()))
    return "".join(
    f"""/* module: {module_name} */ """
+"".join(f"{statement}\n" for statement in module_statements)+f"""
"""
    for module_name, module_statements in global_imports.items()
) + source_updated
