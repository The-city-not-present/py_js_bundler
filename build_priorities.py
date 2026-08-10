

class ErrorCircularDependency(Exception):
    """Raised on circular dependency"""


def process(modules,starting):

    def process_module(module_path,chain_visited=[]):
        something_changed = False
        module = modules[module_path]
        if module.import_order is None:
            return something_changed
        for dep in module.dependencies:
            if dep in chain_visited:
                raise ErrorCircularDependency(f'Circular dependency: "{dep}" from "{module_path}"')
            dep_module = modules[dep]
            if dep_module.import_order is None or dep_module.import_order<module.import_order+1:
                something_changed = True
                dep_module.import_order = module.import_order + 1
            result_nested = process_module(dep,[]+chain_visited+[module_path])
            something_changed = something_changed or result_nested
        return something_changed

    process_module(starting,[])

    print(f'[DEBUG-priorities]: \n\n{"\n".join([str(path)+': \n'+str(modules[path]) for path in modules.keys()])}')

    if len(modules)>0:
        all_have_order = True
        for _, module in modules.items():
            all_have_order = all_have_order and (module.import_order is not None)
        if not all_have_order:
            raise Exception('Building tree of imported modules: not all have import order assigned - failed')

    modules_sorted = sorted(
        modules.keys(),
        key = lambda module_path: -modules[module_path].import_order
    )

    return modules_sorted
