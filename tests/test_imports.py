"""Tests for ``import``-statement handling (``src.process_imports``)."""

from pathlib import Path

import pytest

from ..src.common_defs import Module
from ..src.process_imports import ProcessImportsError
from .helpers import DEFAULT_PROJECT_ROOT, as_pytest_params, bundle_imports
from .cases.imports import IMPORT_CASES


def _modules():
    lib = Module(
        path=DEFAULT_PROJECT_ROOT / "lib.js",
        source="export default 1; export const x = 1;",
        name="lib",
        dependencies=[],
        import_order=1,
    )
    vue = Module(
        path=Path("global://vue"),
        source="vue",
        name="vue_global",
        dependencies=[],
        import_order=1,
    )
    return {
        DEFAULT_PROJECT_ROOT / "lib.js": lib,
        "global://vue": vue,
    }


@pytest.mark.parametrize("case", as_pytest_params(IMPORT_CASES))
def test_import_statement(case):
    out = bundle_imports(case.source, _modules())

    for fragment in case.expected_fragments:
        assert fragment in out
    if case.strip_import:
        assert "import" not in out


@pytest.mark.parametrize(
    "source",
    [
        "import ;",
        "import { aaa }",
        "import { aaa } from",
    ],
)
def test_malformed_imports_raise(source):
    with pytest.raises(ProcessImportsError):
        bundle_imports(source, _modules())


def test_dynamic_import_is_left_untouched():
    assert bundle_imports("import('./x');", _modules()) == "import('./x');"


def test_import_meta_is_left_untouched():
    assert bundle_imports("import.meta.url;", _modules()) == "import.meta.url;"
