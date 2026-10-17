"""Shared helpers and case-generation machinery for the test-suite.

The bundler is driven by small, focused functions (``src.process_exports``,
``src.process_imports``, ...).  Instead of writing one test per import/export
variant, the suite describes the variants as data ("cases") and generates a
pytest test for each of them.

``ExportCase`` and ``ImportCase`` are the schema for that data, and
:func:`as_pytest_params` turns a list of cases into pytest parameters, attaching
an ``xfail`` marker to every case that is known to be unsupported today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from ..src.common_defs import Module
from ..src.process_exports import process_js
from ..src.process_imports import process as process_imports


DEFAULT_MODULE_NAME = "module_0"
# A stable, non-existent directory used only as a base for resolving relative
# import specifiers in unit tests (nothing is ever read from it).
DEFAULT_PROJECT_ROOT = Path("/tmp/py_js_bundler_unit").resolve()


def make_module(source, *, name=DEFAULT_MODULE_NAME, path=None) -> Module:
    """Build a :class:`Module` for a unit-level test."""
    if path is None:
        path = DEFAULT_PROJECT_ROOT / "main.js"
    return Module(
        path=Path(path).resolve(),
        source=source,
        name=name,
        dependencies=[],
        import_order=0,
    )


def bundle_exports(source, *, name=DEFAULT_MODULE_NAME, path=None, config=None) -> str:
    """Run the export-processing stage on a single source string."""
    return process_js(make_module(source, name=name, path=path), config or {})


def bundle_imports(source, modules, *, name=DEFAULT_MODULE_NAME, path=None, config=None) -> str:
    """Run the import-processing stage on a single source string."""
    if path is None:
        path = DEFAULT_PROJECT_ROOT / "main.js"
    config = config or {
        "project_root": DEFAULT_PROJECT_ROOT,
        "aliases": [],
    }
    return process_imports(make_module(source, name=name, path=path), modules, config)


def extract_return_keys(output: str) -> tuple[str, ...]:
    """Extract the top-level keys of the object returned by a bundled module.

    ``process_exports`` emits a template of the form::

        return {
            aaa,
            bbb: ccc,
            default: ddd,
        };

    This helper returns ``("aaa", "bbb", "default")`` for that example.  The
    generated body is flat (a comma-separated list of ``name`` / ``alias: name``
    entries), so a simple comma split is sufficient.
    """
    match = re.search(r"return\s*\{(?P<body>.*?)\}\s*;", output, re.DOTALL)
    if not match:
        return ()
    keys = []
    for part in match.group("body").split(","):
        part = part.strip()
        if not part:
            continue
        key = part.split(":", 1)[0].strip()
        keys.append(key)
    return tuple(keys)


@dataclass(frozen=True)
class ExportCase:
    """One ``export``-statement variant."""

    id: str
    source: str
    status: str = "pass"  # "pass" | "xfail"
    reason: str = ""
    # Keys expected in the object returned by the bundled module *once the case
    # is supported*.  Used to assert semantic correctness for passing cases and
    # to detect "it started working" for xfail cases.
    expected_keys: tuple[str, ...] = ()
    # Whether the bundler must strip the ``export`` keyword from the body.
    strip_export: bool = True


@dataclass(frozen=True)
class ImportCase:
    """One ``import``-statement variant."""

    id: str
    source: str
    status: str = "pass"  # "pass" | "xfail"
    reason: str = ""
    # Substrings that must appear in the transformed output once supported.
    expected_fragments: tuple[str, ...] = ()
    # Whether the bundler must strip the ``import`` keyword from the body.
    strip_import: bool = True


def as_pytest_params(cases):
    """Turn a list of cases into pytest parameters.

    ``xfail`` cases are marked ``pytest.mark.xfail(strict=True)``: they are
    expected to fail *today*, and the strict marker turns an unexpected pass
    into a test failure once someone implements the missing feature — which is
    the signal to remove the ``xfail`` marker.
    """
    params = []
    for case in cases:
        marks = ()
        if case.status == "xfail":
            marks = (pytest.mark.xfail(reason=case.reason or "not supported yet", strict=True),)
        params.append(pytest.param(case, marks=marks, id=case.id))
    return params
