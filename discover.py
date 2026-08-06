
import re

from .common_defs import Module, resolve_import


RE_IMPORT_STATEMENT = re.compile(
    r'^\s*import\s+(?:.+?\s+from)?\s+[\'"](.+?)[\'"]\s*?;?\s*$',
    re.M,
)


def process(file):
    """Add description..."""
    modules = {}


    global_counter = {'counter':0}
    def get_next_module_name():
        knt = global_counter.get("counter")
        name = f'module_{knt}'
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
        dependencies = []

        source = this_module_path.read_text(encoding='utf-8')

        print(f'[DEBUG-discovery]: inspecting children') # debug
        for dep in RE_IMPORT_STATEMENT.finditer(source):
            dep_module = dep.group(1)
            print(f'[DEBUG-discovery]: found: {dep_module}') # debug
            if not dep_module.startswith('./'):
                print(f'[DEBUG-discovery]: path is not relative, skipping') # debug
                continue
            dep_module_path = resolve_import(this_module_path, dep_module)
            print(f'[DEBUG-discovery]: path is: {dep_module_path}') # debug
            dependencies.append(dep_module_path)
            print(f'[DEBUG-discovery]: call recursively for {dep_module_path}') # debug
            discover_modules(dep_module_path)

        source = f'\n// ===== {this_module_path} =====\n' + source

        print(f'[DEBUG-discovery]: done with {file}') # debug
        modules[file] = Module(
            path = file,
            source = source,
            name = module_name,
            dependencies = dependencies,
            import_order = None,
        )

    discover_modules(file)

    return modules
