"""Tests for the shared import-statement parser (``src.parse_import``)."""

import pytest

from ..src.parse_import import ImportParseError, parse_import_statement
from ..src.tokenize_js.tokenize import process as tokenize_js


def _parse(source):
    tokens = tokenize_js(source)
    for index, token in enumerate(tokens):
        if token.kind == 'IDENT' and token.value == 'import':
            return parse_import_statement(tokens, index)
    return None


@pytest.mark.parametrize(
    "source, specifier, side_effect, bindings",
    [
        ("import './lib';", "./lib", True, None),
        ('import "./lib";', "./lib", True, None),
        ("import aaa from './lib';", "./lib", False, "aaa"),
        ("import { aaa } from './lib';", "./lib", False, "{ aaa }"),
        ("import { aaa, bbb } from './lib';", "./lib", False, "{ aaa, bbb }"),
        ("import aaa, { bbb, ccc } from './lib';", "./lib", False, "aaa, { bbb, ccc }"),
        ("import * as ns from './lib';", "./lib", False, "* as ns"),
        ("import aaa, * as ns from './lib';", "./lib", False, "aaa, * as ns"),
        ("import { from } from './lib';", "./lib", False, "{ from }"),
        ("import { default as aaa } from './lib';", "./lib", False, "{ default as aaa }"),
    ],
)
def test_parse_import_statement(source, specifier, side_effect, bindings):
    statement = _parse(source)
    assert statement is not None
    assert statement.specifier == specifier
    assert statement.side_effect == side_effect
    assert (statement.bindings is None) == (bindings is None)
    if bindings is not None:
        assert statement.bindings.strip() == bindings


def test_dynamic_import_is_not_a_static_import():
    assert _parse("import('./x');") is None
    assert _parse("const x = import('./x');") is None


def test_import_meta_is_not_a_static_import():
    assert _parse("import.meta.url;") is None


@pytest.mark.parametrize(
    "source",
    [
        "import ;",
        "import { aaa }",
        "import { aaa } from",
        "import aaa from './lib' junk",
    ],
)
def test_malformed_import_raises(source):
    with pytest.raises(ImportParseError):
        _parse(source)
