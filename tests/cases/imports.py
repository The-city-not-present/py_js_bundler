"""Data + generators for ``import``-statement test cases."""

from ..helpers import ImportCase


def _case(cid, source, *, fragments=(), status="pass", reason="", strip=True):
    return ImportCase(
        id=cid,
        source=source,
        status=status,
        reason=reason,
        expected_fragments=fragments,
        strip_import=strip,
    )


def side_effect_imports():
    return [
        _case("sideeffect_relative_single", "import './lib';", fragments=("lib;",)),
        _case("sideeffect_relative_double", 'import "./lib";', fragments=("lib;",)),
        _case("sideeffect_bare", "import 'vue';", fragments=("vue_global;",)),
    ]


def default_imports():
    return [
        _case("default_relative", "import aaa from './lib';", fragments=("const aaa = lib.default;",)),
        _case("default_relative_extension", "import aaa from './lib.js';", fragments=("const aaa = lib.default;",)),
        _case("default_bare", "import aaa from 'vue';", fragments=("const aaa = vue_global.default;",)),
    ]


def named_imports():
    return [
        _case("named_single", "import { aaa } from './lib';", fragments=("const { aaa } = lib;",)),
        _case("named_multiple", "import { aaa, bbb } from './lib';", fragments=("const { aaa, bbb } = lib;",)),
        _case("named_trailing_comma", "import { aaa, bbb, } from './lib';", fragments=("const { aaa, bbb, } = lib;",)),
        _case("named_aliased", "import { aaa as bbb } from './lib';", fragments=("const { aaa as bbb } = lib;",)),
        _case("named_from_binding", "import { from } from './lib';", fragments=("const { from } = lib;",)),
        _case("named_default_as", "import { default as aaa } from './lib';", fragments=("const { default as aaa } = lib;",)),
        _case("named_bare", "import { aaa } from 'vue';", fragments=("const { aaa } = vue_global;",)),
    ]


def mixed_imports():
    return [
        _case(
            "default_plus_named",
            "import aaa, { bbb, ccc } from './lib';",
            fragments=("const aaa = lib.default;", "const { bbb, ccc } = lib;"),
        ),
        _case(
            "default_plus_named_aliased",
            "import aaa, { bbb as ccc } from './lib';",
            fragments=("const aaa = lib.default;", "const { bbb as ccc } = lib;"),
        ),
        _case(
            "default_plus_named_bare",
            "import aaa, { bbb } from 'vue';",
            fragments=("const aaa = vue_global.default;", "const { bbb } = vue_global;"),
        ),
    ]


def namespace_imports():
    return [
        _case("namespace", "import * as ns from './lib';", status="xfail", reason="namespace imports not supported"),
        _case("namespace_with_default", "import aaa, * as ns from './lib';", status="xfail", reason="namespace imports not supported"),
    ]


IMPORT_CASES = (
    side_effect_imports()
    + default_imports()
    + named_imports()
    + mixed_imports()
    + namespace_imports()
)
