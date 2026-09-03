#!/usr/bin/env python3
from pathlib import Path


from .common_defs import Module
from .scan_project import autodetect_project_config
from .discover import process as discover_modules
from .build_priorities import process as update_import_order
from .process_imports import process as process_imports
from .process_exports import process as process_exports
from .process_global_imports import process as process_create_scritps_global_imports
from .helper_classify_spec_type import classify_module_specifier, ModuleSpecifierType as ModuleType




def process( starting_file, config: dict|None = None ) -> str:

    starting_file = Path(starting_file).resolve()

    config = autodetect_project_config( starting_file, config )

    modules = discover_modules( starting_file, config )

    modules[starting_file].import_order = 0
    modules_sorted = update_import_order(modules,starting_file)

    for module_path in modules.keys():
        module = modules[module_path]

        if str(module_path).startswith('global:'):
            module.source = process_create_scritps_global_imports(module,config)
        else:
            module.source = process_exports(module,config)
            module.source = process_imports(module,modules,config)

    txt = '\n\n\n'.join([modules[a].source for a in modules_sorted])

    return txt
