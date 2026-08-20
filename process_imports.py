
import re
from pathlib import Path

from .common_defs import resolve_import
from .tokenize_js_scripts import process as tokenize_js
from .helper_classify_module_type import classify_module_specifier, Type as ModuleType





class ProcessImportsError(Exception):
    """Raised when imports processing fails."""

    def __init__(self, msg, *args, **kwargs):
        super().__init__(f"Error processing imports: {msg}", *args, **kwargs)

def process(module,modules_dicts):

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

            def next_skipping_by_condition(index_current,check):
                i = index_current
                while i<len(tokens) and check(tokens[i]):
                    i += 1
                return i

            def next_non_zero(index_current,including_br=True):
                if including_br:
                    whitespace_token_types = ('SPACE','SPACEBR',)
                else:
                    whitespace_token_types = ('SPACE',)
                return next_skipping_by_condition(index_current,lambda token: token.kind in whitespace_token_types)

            i = index_current
            i = next_non_zero(i+1)

            if i>len(tokens)-1:
                raise ProcessModuleError(f'Unexpected end of string after "import"')

            if tokens[i].kind=='STRING':
                # import './lib';
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                # # if not name.startswith('./') and not name.startswith('../'):
                # if classify_module_specifier(name) in (ModuleType.BARE,):
                #     # source_updated += tokens[index_current].value
                #     # index_current += 1
                #     i = next_non_zero(i+1,including_br=False)
                #     if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                #         raise ProcessModuleError(f'import \'module\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                #     full_import_string = ''.join([tokens[i].value for i in range(index_current,i+1)])
                #     imported_from_this_global_module = global_imports.get(name,[])
                #     print(f'[DEBUG-imports]: ({module.path}) captured global module: {name}, with statement: "{full_import_string}"')
                #     imported_from_this_global_module.append(full_import_string)
                #     global_imports[name] = imported_from_this_global_module
                #     index_current = i+1
                #     continue
                if classify_module_specifier(name) in (ModuleType.BARE,):
                    import_module_path = resolve_import('global://',name)
                else:
                    import_module_path = resolve_import(module.path,name)
                imported_module = modules_dicts.get(import_module_path)
                if not imported_module:
                    raise ProcessModuleError(f'Failed to resolve import: path = "{name}", resolved path = "{import_module_path}", type = "{classify_module_specifier(name)}". module object == "{imported_module}"')
                source_updated += '\n' + imported_module.name + ';\n\n'
                global_imports
                i = next_non_zero(i+1,including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                    raise ProcessModuleError(f'import \'./something\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                index_current = i+1
                continue

            else:
                # import aaa, { bbb, ccc } from './lib';

                spec_index_start = i
                i = next_skipping_by_condition(i,lambda token: not(token.value=='from' and token.kind=='IDENT'))
                spec_index_end = i-1
                specs = ''
                for i in range(spec_index_start,spec_index_end+1):
                    specs += tokens[i].value

                i = next_non_zero(i+1)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "import"')
                assert tokens[i].value=='from'
                i += 1
                i = next_non_zero(i+1)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "import"')

                assert tokens[i].kind == 'STRING'
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                # # if not name.startswith('./') and not name.startswith('../'):
                # if classify_module_specifier(name) in (ModuleType.BARE,):
                #     # source_updated += tokens[index_current].value
                #     # index_current += 1
                #     i = next_non_zero(i+1,including_br=False)
                #     if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                #         raise ProcessModuleError(f'import \'module\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                #     full_import_string = ''.join([tokens[i].value for i in range(index_current,i+1)])
                #     imported_from_this_global_module = global_imports.get(name,[])
                #     imported_from_this_global_module.append(full_import_string)
                #     print(f'[DEBUG-imports]: ({module.path}) captured global module: {name}, with statement: "{full_import_string}"')
                #     global_imports[name] = imported_from_this_global_module
                #     index_current = i+1
                #     continue
                if classify_module_specifier(name) in (ModuleType.BARE,):
                    import_module_path = resolve_import('global://',name)
                else:
                    import_module_path = resolve_import(module.path,name)
                imported_module = modules_dicts.get(import_module_path)
                if not imported_module:
                    raise ProcessModuleError(f'Failed to resolve import: path = "{name}", resolved path = "{import_module_path}", type = "{classify_module_specifier(name)}". module object == "{imported_module}"')

                i = next_non_zero(i+1,including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
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
