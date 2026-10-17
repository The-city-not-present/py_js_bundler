"""Tests for ``export``-statement handling (``src.process_exports``)."""

import pytest

from ..src.process_exports import ProcessExportsError
from .helpers import as_pytest_params, bundle_exports, extract_return_keys
from .cases.exports import EXPORT_CASES


@pytest.mark.parametrize("case", as_pytest_params(EXPORT_CASES))
def test_export_statement(case):
    """Every supported export variant is transformed into an IIFE whose
    returned object exposes the expected keys; unsupported variants are marked
    xfail and expected to fail until they are implemented."""
    out = bundle_exports(case.source)

    if case.expected_keys:
        assert extract_return_keys(out) == case.expected_keys
    if case.strip_export:
        assert "export" not in out


@pytest.mark.parametrize(
    "source",
    [
        "export;",
        "export default;",
        "export default function;",
        "export { aaa;",
        "export { aaa } junk",
    ],
)
def test_malformed_exports_raise(source):
    with pytest.raises(ProcessExportsError):
        bundle_exports(source)


def test_multiple_default_exports_raise():
    with pytest.raises(ProcessExportsError):
        bundle_exports("export default aaa;\nexport default bbb;\n")
