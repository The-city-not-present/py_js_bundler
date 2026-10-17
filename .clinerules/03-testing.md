# Testing

- **Development tests** (verify program functionality). These live in `tests/` and are **not** included in the final bundle.
- `tests-real-sensitive-data/` is a typical folder for test files that should not be commited - real tests with sensitive data, or temporary personal test files that should not be commited.
- A working example: I can give you a working example: js files are here `/Users/andrej/work/gitgui/src/frontend/app_js`, target, the bundle, is here: `/Users/andrej/work/gitgui/src/frontend/GENERATED/app.js`, the script that makes the bundle is `/Users/andrej/work/gitgui/build.sh` that calls `"$pythonexecutable" build_templates.py --program build --resource app_js --dest src/frontend/GENERATED` that calls `/Users/andrej/work/gitgui/build_templates.py` that calls `build_app_js()` that calls this project here.

## Running the tests

Run from the repository root:

```bash
python3 -m pytest        # or: pytest
```

`pyproject.toml` already sets `testpaths = ["tests"]`, so no arguments are needed.

## Import convention for tests

This repository can be embedded as a submodule in a larger project (see the architecture notes), and a parent project may define its own top-level `src` package that shadows this repository's `src`. Therefore test modules must reach the package under test and the shared helpers via **relative imports**, never `from src... import ...`:

```python
from ..src.run import process
from .helpers import ...
from .cases.exports import ...
```

## Marking unimplemented features

Unsupported-but-valid JavaScript is described as case data in `tests/cases/*.py` and turned into tests by `as_pytest_params()` in `tests/helpers.py`. Cases marked `xfail` are attached with `pytest.mark.xfail(strict=True)`, so a case that unexpectedly starts passing (`XPASS(strict)`) fails the suite on purpose — that is the signal to remove the `xfail` marker for the now-implemented case.
