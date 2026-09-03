import os
from pathlib import Path
import json
from collections.abc import (
    Iterable,
    # Iterator,
    # Mapping,
    # Sequence,
    # Callable,
)
import sys # for error reporting


# STDOUT_COLOR_RED = "\033[91m"
STDOUT_COLOR_RED = "\033[31m"
STDOUT_COLOR_RESET = "\033[0m"
STDOUT_COLOR_GREEN = "\033[32m"



known_package_root_file_patterns: Iterable = (
    'jsconfig.json',
    'tsconfig.json',
    'package.json',
)


def parse_jsconfig_json(filename:Path,existing_config:dict) -> dict:
    result = {**existing_config}
    result['aliases'] = result.get('aliases',None) or []
    cfg = json.load(open(filename))
    try:
        if 'compilerOptions' in cfg:
            try:
                cfg_compiler_options = cfg['compilerOptions'] or {}
                paths = cfg_compiler_options.get('paths',None)
                if paths:
                    try:
                        for path_spec, path_resolution_value in paths.items():
                            for path_resolution_candidate in path_resolution_value:
                                result['aliases'].append((path_spec, path_resolution_candidate,))
                    except Exception as e:
                        print(
                            f'{STDOUT_COLOR_RED}PYJSBUNDLER: Warning: parse {filename} config: failed to parse compilerOptions.paths section\n{e}{STDOUT_COLOR_RESET}',
                            file=sys.stderr)
                        pass
            except Exception as e:
                print(f'{STDOUT_COLOR_RED}PYJSBUNDLER: Warning: parse {filename} config: failed to parse compilerOptions.paths section\n{e}{STDOUT_COLOR_RESET}', file=sys.stderr)
                pass
    except Exception as e:
        print(f'{STDOUT_COLOR_RED}PYJSBUNDLER: Warning: parse {filename} config: failed to parse compilerOptions section\n{e}{STDOUT_COLOR_RESET}', file=sys.stderr)
        pass
    return result

def parse_tsconfig_json(filename:Path,existing_config:dict) -> dict:
    return parse_jsconfig_json(filename,existing_config)

def parse_package_json(filename:Path,existing_config:dict) -> dict:
    result = {**existing_config}
    result['aliases'] = result.get('aliases',None) or []
    cfg = json.load(open(filename))
    if 'name' in cfg:
        result['name'] = cfg['name'] # gibberish, useless
    if 'version' in cfg:
        result['version'] = cfg['version'] # gibberish, useless
    return result

def parse_vite_config_js(filename:Path,existing_config:dict) -> dict:
    result = {**existing_config}
    result['aliases'] = result.get('aliases',None) or []
    # .js is not .json, we need full js interpreter here, to parse function calls of fileURLToPath(new URL('./src', import.meta.url))
    # this is not realistically possible
    # cfg = json.load(open(filename))
    return result


processors = {
    'package.json': parse_package_json,
    'jsconfig.json': parse_jsconfig_json,
    'tsconfig.json': parse_tsconfig_json,
    'vite.config.js': parse_vite_config_js,
}


def did_reach_stop_folder(current, config):
    if not config:
        config = {}

    stop_at = config.get("project_root")

    if stop_at is None:
        return False

    stop_at = Path(stop_at).resolve()
    current = Path(current).resolve()

    try:
        if os.path.samefile(current, stop_at):
            return True
        if os.path.samefile(current, Path.home()):
            return True
    except (FileNotFoundError, OSError):
        return False
    return False


# def scan_for_project_configs(path, config: dict|None = None):
#     """
#     Search for files in `path` and its parent directories.
#
#     Args:
#         path: Starting directory or file.
#         stop_at: Directory at which to stop searching. This directory
#                  itself is searched, but its parent is not.
#
#     Returns:
#         set of found files.
#     """
#
#     path = Path(path).resolve()
#
#     file_patterns = set(known_file_patterns)
#
#     # If the input is a file, start in its containing directory.
#     if path.is_file():
#         current = path.parent
#     elif path.is_dir():
#         current = path
#     else:
#         raise ValueError(f"Path does not exist: {path}")
#
#     result = ()
#
#     if stop_at is not None:
#         stop_at = Path(stop_at).resolve()
#
#         # Make sure the stop directory is actually an ancestor
#         # (or the starting directory itself).
#         try:
#             current.relative_to(stop_at)
#         except ValueError:
#             raise ValueError(
#                 f"stop_at ({stop_at}) is not an ancestor of {current}"
#             )
#
#     while True:
#         # Scan this directory.
#         for filename in file_patterns:
#             candidate = current / filename
#
#             if candidate.is_file():
#                 yield candidate
#
#         if did_reach_stop_folder(current,config):
#             break
#
#         # Reached filesystem root.
#         parent = current.parent
#         if parent == current:
#             break
#
#         current = parent

def scan_for_project_root(path, known_file_patterns, config: dict|None = None) -> Path:
    """
    Search for files in `path` and its parent directories.

    Args:
        path: Starting directory or file.
        stop_at: Directory at which to stop searching. This directory
                 itself is searched, but its parent is not.

    Returns:
        path.
    """

    path = Path(path).resolve()

    if config is None:
        config = {}

    file_patterns = set(known_file_patterns)

    # If the input is a file, start in its containing directory.
    if path.is_file():
        current = path.parent
    elif path.is_dir():
        current = path
    else:
        raise ValueError(f"Path does not exist: {path}")

    while True:
        # Scan this directory.
        for filename in file_patterns:
            candidate = current / filename

            if candidate.is_file():
                return current

        if did_reach_stop_folder(current,config):
            break

        # Reached filesystem root.
        parent = current.parent
        if parent == current:
            break

        current = parent

    return current

def autodetect_project_config(starting_file: str, config: dict|None = None) -> dict:

    if not config:
        config = {}

    project_root = scan_for_project_root(starting_file, known_package_root_file_patterns,config)
    project_root = Path(project_root).resolve()
    config['project_root'] = project_root

    for known_file_name, known_file_processor in reversed(processors.items()):
        known_file = project_root / known_file_name
        if known_file.is_file():
            updated_config = known_file_processor(known_file,config)
            config = {
                **config,
                **updated_config, # new that is earlier in the list should override old that is further in the list - that's why iterating in "reverse" order
            }
            config = config

    return config
