
import re

from .common_defs import Module, resolve_import
from .helper_classify_module_type import classify_module_specifier, Type as ModuleType


RE_IMPORT_STATEMENT = re.compile(
    r'^\s*import\s*(?:.+?\s+from\b)?\s*[\'"](.+?)[\'"]\s*?;?\s*$',
    re.M,
)


def process(file):
    """Add description..."""
    modules = {}


    global_counter = {'counter':0}
    def get_next_module_name(is_global=False):
        knt = global_counter.get("counter")
        appended = '_global' if is_global else ''
        name = f'module{appended}_{knt}'
        global_counter['counter'] = knt+1
        return name



    def discover_modules(this_module_path):
        """Add description..."""

        file = this_module_path.resolve()

        print(f'[DEBUG-discovery]: inspecting module: {file}') # debug

        if this_module_path in modules:
            print(f'[DEBUG-discovery]: already loaded, skip') # debug
            return

        module_name = get_next_module_name()

        source = this_module_path.read_text(encoding='utf-8')

        import_specs_here = [ dep.group(1) for dep in RE_IMPORT_STATEMENT.finditer(source) ]
        module = Module(
            path = file,
            source = source,
            name = module_name,
            dependencies = [],
            import_order = None,
        )
        modules[file] = module

        print(f'[DEBUG-discovery]: inspecting children') # debug
        dependencies = []
        for dep_module in import_specs_here:
            print(f'[DEBUG-discovery]: found: {dep_module}') # debug
            if classify_module_specifier(dep_module) in (ModuleType.BARE,):
                # raise ErrorNotImplemented('Bare imports: not implemented')
                dep_module_path = resolve_import('global://',dep_module)
                dependencies.append(dep_module_path)
                if dep_module_path not in modules:
                    modules[dep_module_path] = Module(
                        path = dep_module_path,
                        source = dep_module,
                        name = get_next_module_name(is_global=True),
                        dependencies = [],
                        import_order = None,
                    )
                continue
            dep_module_path = resolve_import(this_module_path, dep_module)
            print(f'[DEBUG-discovery]: path is: {dep_module_path}') # debug
            dependencies.append(dep_module_path)
            print(f'[DEBUG-discovery]: call recursively for {dep_module_path}') # debug

        for dep_module in import_specs_here:
            if classify_module_specifier(dep_module) in (ModuleType.BARE,):
                continue
            dep_module_path = resolve_import(this_module_path, dep_module)
            discover_modules(dep_module_path)

        module.dependencies = dependencies

        print(f'[DEBUG-discovery]: done with {file}') # debug

    discover_modules(file)

    return modules
