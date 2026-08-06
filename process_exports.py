
import re


from .tokenize_js_scripts import process as tokenize_js


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

def process(module):

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
    while index_current<len(tokens):
        token = tokens[index_current]
        if token.kind=='IDENT' and token.value=='export':

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
                return next_skipping_by_condition(index_current, lambda token: token.kind in whitespace_token_types)

            def next_skip_to_func_after_async(index_current):
                i = index_current
                i = next_skipping_by_condition(index_current, lambda token: token.kind in ('SPACE','SPACEBR','COMMENT',))
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string: expected "function" after "async"')
                if tokens[i].value=='function':
                    return i
                else:
                    raise ProcessModuleError(f'Unexpected end of string: expected "function" after "async"')


            i = index_current
            i = next_non_zero(i+1)

            if i>len(tokens)-1:
                raise ProcessModuleError(f'Unexpected end of string after "export"')

            if tokens[i].value=='default':
                i = next_non_zero(i+1)
                if tokens[i].value in ('function','class','async',):
                    index_current = i
                    if tokens[i].value in ('async',):
                        i = next_skip_to_func_after_async(i+1)
                    i = next_non_zero(i+1)
                    if i>len(tokens)-1:
                        raise ProcessModuleError(f'Unexpected end of string after "export"')
                    name = tokens[i]
                    if name.kind not in ('IDENT',):
                        raise ProcessModuleError(f'export... default... function/class/... and then expected an identifier, got "{name.value}"')
                    name = name.value
                    default_exports.append(name)
                    continue
                else:
                    name = tokens[i]
                    if name.kind not in ('IDENT','NUM',):
                        raise ProcessModuleError(f'export... default... and then expected an identifier, got "{name.value}" ({name.kind})')
                    name = name.value
                    default_exports.append(name)
                    i = next_non_zero(i+1,including_br=False)
                    if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                        raise ProcessModuleError(f'export default IDENT, and then expected EOD, newline, or semicolon, got "{name.value}"')
                    index_current = i+1
                    continue
            elif tokens[i].value=='{':
                # use regex
                exports = []
                index_spec_start = i
                i = next_non_zero(i+1)
                index_spec_body_start = i
                i = next_skipping_by_condition(i,lambda token: token.value!='}')
                index_spec_end = i
                index_spec_body_end = index_spec_end - 1
                spec = ''
                for i in range(index_spec_body_start,index_spec_body_end+1):
                    spec += tokens[i].value
                spec_parts = [s.strip() for s in spec.split(',')]
                for spec_part in spec_parts:
                    spec_name, spec_alias = None, None
                    matches = re.match(r'^\s*(\w+)\s+as\s+(\w+)\s*$',spec_part)
                    if matches:
                        spec_name = matches[1]
                        spec_alias = matches[2]
                    else:
                        matches = re.match(r'^\s*(\w+)\s*$',spec_part)
                        if matches:
                            spec_name = matches[1]
                            spec_alias = None
                        else:
                            raise ProcessModuleError(f'Unexpected syntax within export {{ ... }} : "{spec}"')
                    if not spec_alias:
                        exports.append(spec_name)
                    else:
                        exports.append(f'{spec_alias}: {spec_name}')
                i = next_non_zero(index_spec_end+1,including_br=False)
                if not ( i>len(tokens)-1 or tokens[i].kind=='SPACEBR' or tokens[i].value==';' ):
                    raise ProcessModuleError(f'export {{ aaa, bbb }}, and then expected EOD, newline, or semicolon, got "{name.value}"')
                index_current = i+1
                explicit_exports.append(exports)
                continue
            elif tokens[i].value in ('async','function','const','var','let','class',):
                index_current = i
                if tokens[i].value in ('async',):
                    i = next_skip_to_func_after_async(i+1)
                i = next_non_zero(i+1)
                if i>len(tokens)-1:
                    raise ProcessModuleError(f'Unexpected end of string after "export"')
                name = tokens[i]
                if name.kind!='IDENT':
                    raise ProcessModuleError(f'export... function/let/const/var/class/... and then expected an identifier, got "{name.value}"')
                name = name.value
                named_exports.append(name)
                continue
            else:
                raise ProcessModuleError(f'Unexpected symbol follows "export" statement: "{tokens[i].value}"')
        else:
            source_updated += token.value
        index_current += 1

    if len(default_exports)>1:
        raise ProcessModuleError('Multiple default exports')

    if len(explicit_exports)>0 and ( (len(named_exports)>0) ):
        raise ProcessModuleError('Named/default exports, and explicit export')

    if len(explicit_exports)>1:
        raise ProcessModuleError('Multiple explicit exports in file')

    if len(explicit_exports)>0:
        named_exports = explicit_exports[0]

    return_statements = 'return {\n'+''.join([f'    {name},\n' for name in named_exports])+''+(f'    default: {default_exports[0]},\n' if len(default_exports)>0 else '')+'};'

    return make_template(module_name,source_updated,return_statements)
