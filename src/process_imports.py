
import re

from .common_defs import resolve_import
from .tokenize_js.tokenize import process as tokenize_js
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



def skip_to_next_token_skipping_by_condition(index_current, tokens, check):
    i = index_current
    while i < len(tokens) and check(tokens[i]):
        i += 1
    return i

def skip_to_next_token_non_zero(index_current, tokens, including_br=True):
    if including_br:
        whitespace_token_types = ('SPACE', 'NEWLINE',)
    else:
        whitespace_token_types = ('SPACE',)
    return skip_to_next_token_skipping_by_condition(index_current, tokens, lambda token: token.kind in whitespace_token_types)



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

        if token.value=='import':

            i = index_current
            i = skip_to_next_token_non_zero(i+1, tokens)

            if i>len(tokens)-1:
                raise ProcessModuleError(f'Unexpected end of string after "import"')

            if tokens[i].kind=='STRING':
                # import './lib';
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                if classify_module_specifier_role_for_bundler(name, project_root, module.path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                    import_module_path = resolve_import('global://',name)
                else:
                    import_module_path = resolve_import(module.path,resolve_aliases(name, project_root, module.path, aliases))
                imported_module = modules_dicts.get(import_module_path)
                if not imported_module:
                    raise ProcessModuleError(f'Failed to resolve import: path = "{name}", resolved path = "{import_module_path}", type = "{classify_module_specifier(name)}". module object == "{imported_module}"')
                source_updated += '\n' + imported_module.name + ';\n\n'
                # global_imports # TODO: what is this, "global_imports"? What is this line? Please clarify the meaning
                i = skip_to_next_token_non_zero(i+1, tokens, including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='NEWLINE' or tokens[i].value==';' ):
                    raise ProcessModuleError(f'import \'./something\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                index_current = i+1
                continue

            else:
                # import aaa, { bbb, ccc } from './lib';

                spec_index_start = i
                i = skip_to_next_token_skipping_by_condition(i, tokens, lambda token: not(token.value=='from' and token.kind=='IDENT'))
                spec_index_end = i-1
                specs = ''
                for i in range(spec_index_start,spec_index_end+1):
                    specs += tokens[i].value

                i = skip_to_next_token_non_zero(i+1, tokens)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "import"')
                assert tokens[i].value=='from'
                i += 1
                i = skip_to_next_token_non_zero(i+1, tokens)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "import"')

                assert tokens[i].kind == 'STRING'
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                if classify_module_specifier_role_for_bundler(name, project_root, module.path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                    import_module_path = resolve_import('global://',name)
                else:
                    import_module_path = resolve_import(module.path,resolve_aliases(name, project_root, module.path, aliases))
                imported_module = modules_dicts.get(import_module_path)
                if not imported_module:
                    raise ProcessModuleError(f'Failed to resolve import: path = "{name}", resolved path = "{import_module_path}", type = "{classify_module_specifier(name)}". module object == "{imported_module}"')

                i = skip_to_next_token_non_zero(i+1, tokens, including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='NEWLINE' or tokens[i].value==';' ):
                    raise ProcessModuleError(f'import \'./something\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                index_current = i+1

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
    print(f'[DEBUG-imports]: ({module.path}) global imports captured (raw): {repr(global_imports)}')
    print(f'[DEBUG-imports]: ({module.path}) global imports captured, globally: '+', '.join([name for name in global_imports.keys()]))
    return "".join(
    f"""/* module: {module_name} */ """
+"".join(f"{statement}\n" for statement in module_statements)+f"""
"""
    for module_name, module_statements in global_imports.items()
) + source_updated
