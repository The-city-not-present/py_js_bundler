# js bundler

This is the bundler for js files in python. It is self-written and is very raw. However, it is working surprisingly well. I have plans to extend it.

The goal is to make it possible to bundle js files on a machine that does not have node or vite installed. However, it should be able to handle typical js files that are valid and are making up a typical project with node and vite. We should not require any special adjustments in js files or project structure for this tool to work.

This bundler also supports reading certain kinds of config from typical js config files, including path aliases (for example, `@` for app root).

This might be used as imported module, or included in other repos as submodule. Use cases may vary. It can be used within other project bundled with pinliner (`/Users/andrej/work/gitgui/src_dev_build/lib/pinliner`). This puts certain constraints: 1. use only relative imports, 2. always consider this code can be lifted to a different place in bigger project without changes in code, 3. every folder in path to every module here must contain `__init__.py`, 4. everything used should be in python modules - no static files, assets. Everything used must be importable as a python module.

Please stick to policy of minimal dependencies.