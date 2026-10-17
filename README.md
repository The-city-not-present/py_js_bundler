# py_js_bundler

A small, dependency-free JavaScript bundler written in Python. It takes an
entry `.js` file and produces a single self-contained JavaScript string —
without needing Node, Vite, or any JavaScript runtime.

## Why does this exist?

Sometimes you need to produce a front-end bundle on a machine where only
Python is available — no `node`, no `vite`, no npm. This tool fills that gap:

> bundle a typical Node/Vite project's JavaScript **without a JavaScript
> environment**, using only the Python standard library.

It is designed to work on ordinary, unmodified project code: you should not
have to change your `.js` files, your import style, or your project layout for
it to do its job.

## What it does

Given an entry file, it:

1. **Discovers** every module reachable from that file by following `import`
   statements (resolving relative paths and path aliases).
2. **Topologically orders** the modules so dependencies come before the files
   that import them.
3. **Rewrites** each module into a small `const module_N = (function() { ... })()`
   IIFE that returns its named/default exports, and rewrites `import` statements
   into references to those module objects.

For example, two files:

```js
// lib.js
export function helper() { return 1; }
export default helper;
```

```js
// app.js
import helper from "./lib.js";
export const answer = helper();
```

become (simplified):

```js
const module_1 = (function() {
  function helper() { return 1; }
  return { helper, default: helper };
}());

const module_0 = (function() {
  const helper = module_1.default;
  const answer = helper();
  return { answer };
}());
```

On top of that, it:

- reads **path aliases** (`@` for the app root) from `jsconfig.json` /
  `tsconfig.json` (`compilerOptions.paths`);
- leaves **bare imports** (e.g. `import { createApp } from 'vue'`) as ES module
  imports, because they are expected to be provided by the runtime;
- inlines **CSS imports** by injecting a `<style>` element.

## How to use it

There is no build or install step. The library is plain Python and is used by
importing it and calling `process`:

```python
from py_js_bundler.src.run import process  # exact path depends on your layout

bundle = process("src/frontend/app_js/src/app.js")

with open("GENERATED/app.js", "w", encoding="utf-8") as f:
    f.write(bundle)
```

`process(entry_file, config=None)` returns the bundled JavaScript as a string.
The `config` dict is optional and supports `verbosity` (see below). The project
root is detected automatically by walking up from the entry file looking for
`jsconfig.json`, `tsconfig.json`, or `package.json`.

## Requirements

- **Python 3.10 or newer** (uses modern `X | None` type hints).
- **No third-party packages** — the standard library only.

That is the entire point: it must run anywhere Python runs.

## Is there a build step?

Not for this tool. It is a library that produces the bundle at *runtime* — you
call `process()` and get a string back. (In a larger project, *your own* build
pipeline may call it; this repository itself has nothing to compile.)

## Verbosity / logging

By default the tool is silent: the detailed per-module trace is logged at
`DEBUG` level and does not appear. To see it, either pass `verbosity` in the
`config` dict, or configure the logger directly:

```python
process("app.js", {"verbosity": 2})   # 0 = warnings only, 1 = info, 2+ = debug

# or, once for the whole process:
from py_js_bundler.src.log import configure
configure(2)
```

Warnings (for example, a config file that failed to parse) are shown by
default.

## What is supported

**Exports**

- `export function aaa() {}`, `export async function aaa() {}`
- `export function* aaa() {}`, `export async function* aaa() {}` (generators)
- `export class Aaa {}`
- `export const aaa = ...`, `export let ...`, `export var ...`
- `export default function aaa() {}`, `export default async function ...`,
  `export default class Aaa {}`, `export default function* aaa() {}`,
  `export default async function* aaa() {}`
- anonymous default exports: `export default function() {}`,
  `export default async function() {}`, `export default class {}`,
  `export default function* () {}`, `export default async function* () {}`
- `export default aaa;` (a declared identifier), `export default 42;`
- `export { aaa }`, `export { aaa, bbb }`, `export { aaa as bbb }`,
  `export { aaa as default }`

**Imports**

- `import "./lib";` (side-effect)
- `import aaa from "./lib";`
- `import { aaa, bbb } from "./lib";`, `import { aaa as bbb } from "./lib";`,
  `import { default as aaa } from "./lib";`
- `import aaa, { bbb, ccc } from "./lib";`
- bare imports such as `import { createApp } from "vue"` (left as-is)

**Config**

- path aliases from `jsconfig.json` / `tsconfig.json`, e.g.
  `{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}`
- `.css` imports are inlined as `<style>` injection

## Current limitations

The implementation is deliberately raw: it uses a hand-written tokenizer and
simple parsing rather than a full JavaScript parser. Unsupported-but-valid
JavaScript fails loudly rather than silently mis-bundling. Known gaps today:

- expression defaults: `export default { ... }`, `export default [ ... ]`,
  `export default ( ... )`
- multiple declarators: `export const a = 1, b = 2;` (only `a` is exported)
- re-exports: `export ... from "./lib";`
- namespace imports: `import * as ns from "./lib";`
- circular dependencies raise an error rather than being resolved
- `.vue` files are not handled
- a missing import raises an error (`FileNotFoundError`)

These are tracked as `xfail` cases in the test suite; when one is implemented,
the corresponding test starts passing and its `xfail` marker is removed.

## Project layout

```
src/
  run.py                    entry point: process(entry_file, config)
  discover.py               follows imports, builds the module tree
  parse_import.py           shared "parse an import statement" helper
  process_imports.py        rewrites import statements
  process_exports.py        rewrites export statements
  build_priorities.py       topological ordering
  scan_project.py           finds the project root + path aliases
  tokenize_js/tokenize.py   the tokenizer
  log.py                    logging configuration
tests/                      the test suite (pytest)
```

## Development

Run the tests from the repository root:

```bash
python3 -m pytest
```

## Constraints for embedding this repository

This tool is also meant to be used as an imported module or included in other
repositories as a submodule, and it can be embedded into larger projects (for
example, those bundled with pinliner). That imposes a few rules on the code in
this repository:

1. use only relative imports;
2. assume the code can be lifted to a different location in a larger project
   without changes;
3. every folder in the path to every module here must contain `__init__.py`;
4. everything is a Python module — no static files or assets; everything must be
   importable;
5. minimal dependencies (standard library only).
