"""Tests for import-statement discovery (``src.discover``)."""

import pytest

from ..src.parse_import import extract_import_specifiers


@pytest.mark.parametrize(
    "source, expected",
    [
        # side-effect imports
        ("import './lib';", ["./lib"]),
        ('import "./lib";', ["./lib"]),
        # default / named / namespace imports
        ("import aaa from './lib';", ["./lib"]),
        ("import { aaa } from './lib';", ["./lib"]),
        ("import { aaa, bbb } from './lib';", ["./lib"]),
        ("import { aaa as bbb } from './lib';", ["./lib"]),
        ("import aaa, { bbb, ccc } from './lib';", ["./lib"]),
        ("import * as ns from './lib';", ["./lib"]),
        ("import aaa, * as ns from './lib';", ["./lib"]),
        # ``from`` used as an imported / aliased binding name
        ("import { from } from './lib';", ["./lib"]),
        ("import { default as aaa } from './lib';", ["./lib"]),
        # multi-line import statement
        ("import {\n  aaa,\n  bbb,\n} from './lib';", ["./lib"]),
        # several imports, preserving order
        ("import './a';\nimport './b';", ["./a", "./b"]),
        # no imports
        ("export const x = 1;", []),
        # import-looking text inside opaque constructs is ignored
        ("const t = `import './x';`;", []),
        ("const t = `\nimport './x';\n`;", []),
        ("// import './x';\nconst a = 1;", []),
        ("/*\nimport './x';\n*/\nconst a = 1;", []),
        ('const s = "import \'./x\'";', []),
        ("const r = /import/;", []),
        # dynamic import / import.meta are not static imports
        ("import('./x');", []),
        ("const x = import('./x');", []),
        ("import.meta.url;", []),
        # re-exports are not imports (not followed by discovery)
        ("export { aaa } from './lib';", []),
        ("export * from './lib';", []),
    ],
)
def test_extract_import_specifiers(source, expected):
    assert extract_import_specifiers(source) == expected
