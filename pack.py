#!/usr/bin/env python3
from pathlib import Path


from .common_defs import Module
from .discover import process as discover_modules
from .build_priorities import process as update_import_order
from .process_imports import process as process_imports
from .process_exports import process as process_exports




def process(starting_file) -> str:

    starting_file = Path(starting_file).resolve()
    modules = discover_modules(starting_file)
    modules[starting_file].import_order = 0
    modules_sorted = update_import_order(modules,starting_file)
    for module_path in modules.keys():
        module = modules[module_path]
        module.source = process_imports(module,modules)
        module.source = process_exports(module)

    txt = '\n\n\n'.join([modules[a].source for a in modules_sorted])

    return txt
