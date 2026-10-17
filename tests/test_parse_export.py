"""Tests for the shared export-statement parser (``src.parse_export``)."""

import pytest

from ..src.parse_export import ExportParseError, parse_export_statement
from ..src.tokenize_js.tokenize import process as tokenize_js


def _parse(source):
    tokens = tokenize_js(source)
    for index, token in enumerate(tokens):
        if token.kind == 'IDENT' and token.value == 'export':
            return parse_export_statement(tokens, index)
    return None


@pytest.mark.parametrize(
    "source, kind, names",
    [
        ("export function aaa() {}", "named", ("aaa",)),
        ("export async function aaa() {}", "named", ("aaa",)),
        ("export function* aaa() {}", "named", ("aaa",)),
        ("export class Aaa {}", "named", ("Aaa",)),
        ("export const aaa = 1;", "named", ("aaa",)),
        ("export let aaa = 1;", "named", ("aaa",)),
        ("export var aaa = 1;", "named", ("aaa",)),
        ("export default function aaa() {}", "default", ("aaa",)),
        ("export default async function aaa() {}", "default", ("aaa",)),
        ("export default function* aaa() {}", "default", ("aaa",)),
        ("export default class Aaa {}", "default", ("Aaa",)),
        ("export default aaa;", "default", ("aaa",)),
        ("export default 42;", "default", ("42",)),
        ("export default function() {}", "default", ("_default",)),
        ("export default class {}", "default", ("_default",)),
        ("export { aaa };", "explicit", ("aaa",)),
        ("export { aaa, bbb };", "explicit", ("aaa", "bbb")),
        ("export { aaa as bbb };", "explicit", ("bbb: aaa",)),
        ("export { aaa as default };", "explicit", ("default: aaa",)),
    ],
)
def test_parse_export_statement(source, kind, names):
    statement = _parse(source)
    assert statement is not None
    assert statement.kind == kind
    assert statement.names == names


def test_anonymous_default_prefix():
    assert _parse("export default function() {}").prefix == "function _default"
    assert _parse("export default class {}").prefix == "class _default"
    assert _parse("export default function* () {}").prefix == "function* _default"
    assert _parse("export default async function () {}").prefix == "async function _default"


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
def test_malformed_export_raises(source):
    with pytest.raises(ExportParseError):
        _parse(source)
