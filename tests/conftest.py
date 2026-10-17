"""Pytest configuration for the py_js_bundler test-suite.

This repository can be checked out on its own or embedded as a submodule inside
a larger project (see the architecture notes).  Because a parent project may
already define a top-level ``src`` package that shadows this repository's own
``src``, the test-suite does **not** import ``src`` by its top-level name.
Instead every test/helper module uses relative imports, so the package under
test is always reached as the sibling of this ``tests`` package:

* ``..src`` — the package under test (``from ..src.run import process``),
* ``.helpers`` / ``.cases`` — shared test helpers and case data.

``pyproject.toml`` points pytest at the ``tests`` directory; no ``sys.path``
manipulation is required.
"""
