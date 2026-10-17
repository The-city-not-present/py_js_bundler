
from pathlib import Path # for type checker only

from .common_defs import Module, resolve_import
from .helper_classify_spec_type import (
    ModuleSpecifierBundlerRole,
    classify_module_specifier_role_for_bundler,
    resolve_aliases,
)
from .tokenize_js.tokenize import process as tokenize_js


def _skip_ws(index, tokens):
    """Skip SPACE / NEWLINE / COMMENT tokens."""
    while index < len(tokens) and tokens[index].kind in ('SPACE', 'NEWLINE', 'COMMENT'):
        index += 1
    return index


def _unquote(value):
    """Strip the surrounding quotes of a string/template token."""
    quote = value[0]
    assert quote in ("'", '"', "`")
    assert value[-1] == quote
    return value[1:-1].replace('\\' + quote, quote)


def _find_from(index, tokens):
    """Return the index of the ``from`` keyword of a binding import, or None."""
    n = len(tokens)
    while index < n:
        token = tokens[index]
        if token.kind == 'SEMICOLON':
            return None
        if token.kind == 'IDENT' and token.value == 'from':
            after = _skip_ws(index + 1, tokens)
            if after < n and tokens[after].kind == 'STRING':
                return index
        index += 1
    return None


def extract_import_specifiers(source):
    """Return the module specifiers of all top-level ``import`` statements.

    Strings, template literals, regular expressions and comments are tokenized
    as single opaque tokens, so ``import``-looking text inside them is never
    reported.  Dynamic ``import(...)`` and ``import.meta`` are also ignored.
    """
    tokens = tokenize_js(source)
    specifiers = []
    n = len(tokens)
    i = 0
    while i < n:
        token = tokens[i]
        if token.kind != 'IDENT' or token.value != 'import':
            i += 1
            continue

        after_import = _skip_ws(i + 1, tokens)
        if after_import >= n:
            break

        if tokens[after_import].kind == 'STRING':
            # import './lib';
            specifiers.append(_unquote(tokens[after_import].value))
            i = after_import + 1
            continue

        if tokens[after_import].kind == 'LPAREN':
            # import('./lib') — dynamic import, not a static import.
            i = after_import + 1
            continue

        # import ... from './lib';
        from_index = _find_from(after_import, tokens)
        if from_index is None:
            i += 1
            continue
        specifier_index = _skip_ws(from_index + 1, tokens)
        if specifier_index < n and tokens[specifier_index].kind == 'STRING':
            specifiers.append(_unquote(tokens[specifier_index].value))
            i = specifier_index + 1
        else:
            i += 1

    return specifiers


def process(file: Path | str, config: None | dict = None):
    """Add description..."""
    if not config:
        config = dict()

    aliases = config.get('aliases',{})
    project_root = config.get('project_root',None)

    modules = {}


    global_counter = {'counter':0}
    def get_next_module_name(is_global=False):
        knt = global_counter.get("counter")
        appended = '_global' if is_global else ''
        name = f'module{appended}_{knt}'
        global_counter['counter'] = knt+1
        return name



    def discover_modules(module_path):
        """Add description..."""

        module_path = module_path.resolve()

        print(f'[DEBUG-discovery]: inspecting module: {module_path}') # debug

        if module_path in modules:
            print(f'[DEBUG-discovery]: already loaded, skip') # debug
            return

        module_name = get_next_module_name()

        source = module_path.read_text(encoding='utf-8')

        import_statements_here = extract_import_specifiers(source)
        module = Module(
            path = module_path,
            source = source,
            name = module_name,
            dependencies = [],
            import_order = None,
        )
        modules[module_path] = module

        print(f'[DEBUG-discovery]: inspecting children') # debug
        dependencies = []
        for dependency_module_spec in import_statements_here:
            print(f'[DEBUG-discovery]: found: {dependency_module_spec}') # debug
            #if classify_module_specifier(dependency_module_spec) in (ModuleSpecifierType.BARE,):
            if classify_module_specifier_role_for_bundler(dependency_module_spec, project_root, module_path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                # raise ErrorNotImplemented('Bare imports: not implemented')
                dep_module_path = resolve_import('global://', dependency_module_spec)
                dependencies.append(dep_module_path)
                if dep_module_path not in modules:
                    modules[dep_module_path] = Module(
                        path = dep_module_path,
                        source = dependency_module_spec,
                        name = get_next_module_name(is_global=True),
                        dependencies = [],
                        import_order = None,
                    )
                continue
            dep_module_path = resolve_import(module_path, resolve_aliases(dependency_module_spec, project_root, module.path, aliases))
            print(f'[DEBUG-discovery]: path is: {dep_module_path}') # debug
            dependencies.append(dep_module_path)
            print(f'[DEBUG-discovery]: call recursively for {dep_module_path}') # debug

        for dependency_module_spec in import_statements_here:
            # if classify_module_specifier(dependency_module_spec) in (ModuleSpecifierType.BARE,):
            if classify_module_specifier_role_for_bundler(dependency_module_spec, project_root, module_path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                continue
            dep_module_path = resolve_import(module_path, resolve_aliases(dependency_module_spec, project_root, module.path, aliases))
            discover_modules(dep_module_path)

        module.dependencies = dependencies

        print(f'[DEBUG-discovery]: done with {module_path}') # debug

    discover_modules(file)

    return modules
