
from pathlib import Path # for type checker only

from .common_defs import Module, resolve_import
from .helper_classify_spec_type import (
    ModuleSpecifierBundlerRole,
    classify_module_specifier_role_for_bundler,
    resolve_aliases,
)
from .parse_import import extract_import_specifiers
from .log import logger


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

        logger.debug('[DEBUG-discovery]: inspecting module: %s', module_path)

        if module_path in modules:
            logger.debug('[DEBUG-discovery]: already loaded, skip')
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

        logger.debug('[DEBUG-discovery]: inspecting children')
        dependencies = []
        for dependency_module_spec in import_statements_here:
            logger.debug('[DEBUG-discovery]: found: %s', dependency_module_spec)
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
            logger.debug('[DEBUG-discovery]: path is: %s', dep_module_path)
            dependencies.append(dep_module_path)
            logger.debug('[DEBUG-discovery]: call recursively for %s', dep_module_path)

        for dependency_module_spec in import_statements_here:
            # if classify_module_specifier(dependency_module_spec) in (ModuleSpecifierType.BARE,):
            if classify_module_specifier_role_for_bundler(dependency_module_spec, project_root, module_path, aliases) not in (ModuleSpecifierBundlerRole.PROCESS,):
                continue
            dep_module_path = resolve_import(module_path, resolve_aliases(dependency_module_spec, project_root, module.path, aliases))
            discover_modules(dep_module_path)

        module.dependencies = dependencies

        logger.debug('[DEBUG-discovery]: done with %s', module_path)

    discover_modules(file)

    return modules
