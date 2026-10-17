"""End-to-end tests for the full bundling pipeline (``src.run.process``)."""

import pytest

from ..src.build_priorities import ErrorCircularDependency
from ..src.helper_classify_spec_type import ModuleSpecifierType, classify_module_specifier
from ..src.run import process


def _write_project(tmp_path, files):
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _bundle(tmp_path, files, entry="src/main.js"):
    _write_project(tmp_path, files)
    return process(tmp_path / entry)


def test_bundles_relative_and_alias_imports(tmp_path):
    files = {
        "jsconfig.json": '{"compilerOptions":{"paths":{"@/*":["./src/*"]}}}',
        "src/main.js": (
            "import deepMerge from '@/common_defs/deep_merge';\n"
            "import { helper } from './lib';\n"
            "export const appName = 'demo';\n"
            "console.log(deepMerge, helper, appName);\n"
        ),
        "src/lib.js": "export const helper = () => 1;\nexport default helper;\n",
        "src/common_defs/deep_merge.js": (
            "function deepMerge(a, b) { return Object.assign({}, a, b); }\n"
            "export default deepMerge;\n"
        ),
    }

    bundle = _bundle(tmp_path, files)

    assert "module_0" in bundle
    assert "const appName = 'demo';" in bundle
    assert "const deepMerge = module_1.default;" in bundle
    assert "const { helper } = module_2;" in bundle
    assert "import " not in bundle
    assert "export " not in bundle
    # Dependencies are emitted before the module that imports them.
    assert bundle.index("module_1") < bundle.index("module_0")
    assert bundle.index("module_2") < bundle.index("module_0")


def test_bundles_css_import(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/main.js": "import './styles.css';\nexport const ok = 1;\n",
        "src/styles.css": "body { color: red; }",
    }

    bundle = _bundle(tmp_path, files)

    assert "document.createElement('style')" in bundle
    assert "body { color: red; }" in bundle


def test_bundles_bare_import_as_global(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/main.js": "import { createApp } from 'vue';\nexport const ok = 1;\n",
    }

    bundle = _bundle(tmp_path, files)

    # Bare imports are not bundled; they stay as an ES import of the package
    # and are referenced through a generated global-module object.
    assert "import * as module_global_1 from 'vue';" in bundle
    assert "const { createApp } = module_global_1;" in bundle


def test_import_lookalikes_inside_literals_are_ignored(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/main.js": (
            "const t = `\nimport './does_not_exist';\n`;\n"
            "/*\nimport './also_does_not_exist';\n*/\n"
            "import './real_dep';\n"
            "export const ok = 1;\n"
        ),
        "src/real_dep.js": "export const dep = 1;\n",
    }

    # The ``import``-looking text inside the template literal and block comment
    # must not be resolved (it would raise FileNotFoundError); the real
    # dependency is still followed and bundled.
    bundle = _bundle(tmp_path, files)

    assert "dep" in bundle


def test_circular_dependency_raises(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/a.js": "import { b } from './b';\nexport const a = 1;\n",
        "src/b.js": "import { a } from './a';\nexport const b = 2;\n",
    }

    with pytest.raises(ErrorCircularDependency):
        _bundle(tmp_path, files, entry="src/a.js")


def test_missing_import_raises(tmp_path):
    files = {
        "jsconfig.json": "{}",
        "src/main.js": "import x from './does_not_exist';\nexport const ok = 1;\n",
    }

    with pytest.raises(FileNotFoundError):
        _bundle(tmp_path, files)


def test_classify_module_specifier():
    assert classify_module_specifier("./lib") == ModuleSpecifierType.PATH_RELATIVE
    assert classify_module_specifier("../lib") == ModuleSpecifierType.PATH_RELATIVE
    assert classify_module_specifier("vue") == ModuleSpecifierType.BARE
    assert classify_module_specifier("@/lib") == ModuleSpecifierType.BARE
    assert classify_module_specifier("https://example.com/x.js") == ModuleSpecifierType.URL_ABSOLUTE
    assert classify_module_specifier("/abs/path.js") == ModuleSpecifierType.PATH_ABSOLUTE
