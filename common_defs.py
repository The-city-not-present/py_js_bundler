

from dataclasses import dataclass
from pathlib import Path

@dataclass
class Module:
    path: Path
    source: str
    name: str
    dependencies: list
    import_order: int | None
    def __str__(self):
        # return repr(self)
        return f'''
        path:     {self.path}
        source:   {repr(self.source[:30])}
        name:     {self.name}
        deps:     [ {", ".join([str(d) for d in self.dependencies])} ]
        import_order: {self.import_order}
'''


def resolve_import(base: Path, target: str):
    """Based on module name, returns path to file"""
    # if not target.startswith('./') and not target.startswith('../'):
    #     raise RuntimeError(
    #         f'Only relative imports are supported ({target})'
    #     )
    if f'{base}'.startswith('global:'):
        return f'{base}{target}'
    path = (base.parent / target).resolve()
    if path.suffix == '':
        path = path.with_suffix('.js')
    return path
