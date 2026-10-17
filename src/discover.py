
from pathlib import Path # for type checker only

from .common_defs import Module, resolve_import
from .helper_classify_spec_type import (
    ModuleSpecifierBundlerRole,
    classify_module_specifier_role_for_bundler,
    resolve_aliases,
)
from .parse_import import extract_import_specifiers


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
