
import re
from pathlib import Path

from .common_defs import resolve_import
from .tokenize_js_scripts import process as tokenize_js





class ProcessImportsError(Exception):
    """Raised when imports processing fails."""

    def __init__(self, msg, *args, **kwargs):
        super().__init__(f"Error processing imports: {msg}", *args, **kwargs)

def process(module,modules_dics):

    class ProcessModuleError(ProcessImportsError):
        """Raised when imports processing fails."""

        def __init__(self, msg, *args, **kwargs):
            super().__init__(f'{msg}: in module "{module.path}"', *args, **kwargs)

    source = module.source

    source_updated = ''
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
                raise ProcessModuleError(f'Unexpected end of string after "export"')

            if tokens[i].kind=='STRING':
                # import './lib';
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                import_module_path = resolve_import(module.path,name)
                imported_module = modules_dics.get(import_module_path)
                if not imported_module:
                    print(f'For DEBUGGING, for reference, modules are:\n\n{modules_dics}')
                    raise ProcessModuleError(f'Failed to resolve relative import: path = "{name}", resolved path = "{import_module_path}". module object == "{imported_module}"')
                source_updated += '\n' + imported_module.name + ';\n\n'

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
                    raise ProcessModuleError(f'Unexpected end of string after "export"')
                assert tokens[i].value=='from'
                i += 1
                i = next_non_zero(i+1)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "export"')

                assert tokens[i].kind == 'STRING'
                name_quoted = tokens[i].value.strip()
                quote = name_quoted[0]
                assert quote in ('\'','"','`',)
                assert name_quoted[-1]==quote
                name = name_quoted[1:-1].replace('\\'+quote,quote)
                import_module_path = resolve_import(module.path,name)
                imported_module = modules_dics.get(import_module_path)
                if not imported_module:
                    print(f'For DEBUGGING, for reference, modules are:\n\n{modules_dics}')
                    raise ProcessModuleError(f'Failed to resolve relative import: path = "{name}", resolved path = "{import_module_path}". module object == "{imported_module}"')

                i = next_non_zero(i+1,including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                    raise ProcessModuleError(f'import \'./something\', and then expected EOD, newline, or semicolon, got "{name.value}"')
                index_current = i+1

                if re.match(r'^\s*(\w+)\s*$',specs):
                    matches = re.match(r'^\s*(\w+)\s*$',specs)
                    default_name = matches[1]
                    source_updated += '\n' + f'const {default_name} = {imported_module.name}.default;\n' + ';\n\n'
                elif re.match(r'\s*\{\s*([^\n]*?)\s*\}\s*$',specs):
                    matches = re.match(r'\s*(\{\s*[^\n]*?\s*\})\s*$',specs)
                    specs_named = matches[1]
                    source_updated += '\n' + f'const {specs_named} = {imported_module.name};' + '\n'
                elif re.match(r'\s*(\w+(?:\s+\bas\b\s*\b\w+)?)\s*,\s*\{\s*([^\n]*?)\s*\}\s*$',specs):
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
                    raise ProcessModuleError(f'Not matching') # assert

                source_updated += '\n'
                continue

        else:
            source_updated += token.value

        index_current += 1

    return source_updated
