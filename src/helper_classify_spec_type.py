import os
import re
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

from .common_defs import resolve_import


class ModuleSpecifierType(Enum):
    BARE = 1
    PATH_RELATIVE = 2
    URL_ABSOLUTE = 3
    PATH_ABSOLUTE = 4
    ALIAS_RESOLVABLE = 98

# class Status(str, Enum):
#     PENDING = "pending"
#     RUNNING = "running"
#     COMPLETED = "completed"
#
# print(Status.PENDING.value)  # pending

# class LogLevel(Enum):
#     DEEBUG = 1 # to not have it highlighter by linter and search - I am sometimes searching for word "deb..."
#     INFO = 2
#     ERROR = 3
#
# def log(message: str, level: LogLevel):
#     print(f"[{level.name}] {message}")


class ModuleSpecifierBundlerRole(Enum):
    UNTOUCH = 0
    PROCESS = 1




def glob_to_groups(pattern: str) -> list:
    @dataclass
    class Token:
        kind: str
        value: str
        def as_regex(self) -> str:
            if self.kind in ("LITERAL", "EMPTY",):
                return "(" + re.escape("".join(self.value)) + ")"
            elif self.kind in ("INDEFINITE",):
                return "(" + ".*" + ")"
            elif self.kind in ("WILDCARD",):
                if self.value == "*":
                    return "(" + "[^/]*" + ")"
                if self.value == "?":
                    return "(" + "[^/]" + ")"
                else:
                    raise Exception(f'glob_to_regex: unknown token: {repr(self)}')
            else:
                raise Exception(f'glob_to_regex: unknown token: {repr(self)}')
        def as_txt(self) -> str | None:
            if self.kind in ("LITERAL", "EMPTY",):
                return "".join(self.value)
            else:
                return None
    def tokenize(src: str) -> list[Token]:
        tokens: list[Token] = []
        i = 0
        n = len(src)
        tokens.append(Token("INDEFINITE", ""))
        while i < n:
            last = tokens[-1].kind
            c = src[i]
            # *
            if c=='*':
                if last not in ("LITERAL","EMPTY",):
                    tokens.append(Token("EMPTY", ""))
                tokens.append(Token("WILDCARD", src[i:i+1]))
                i += 1
                continue
            # ?
            elif c=='?':
                if last not in ("LITERAL","EMPTY",):
                    tokens.append(Token("EMPTY", ""))
                tokens.append(Token("WILDCARD", src[i:i+1]))
                i += 1
                continue
            # literal
            else:
                start = i
                i += 1
                while i < n and (src[i] not in ('*','?',)):
                    i += 1
                tokens.append(Token("LITERAL", src[start:i]))
                continue
        last = tokens[-1].kind
        if last not in ("LITERAL", "EMPTY",):
            tokens.append(Token("EMPTY", ""))
        if last not in ("INDEFINITE",):
            tokens.append(Token("INDEFINITE", ""))
        return tokens
    return tokenize(pattern)




def resolve_aliases(name: str, base: Path|str|None, current_module_path, aliases: list[tuple[str,str]]):
    def norm(s):
        return str(s).replace('\\','/')
    def norm_rel(s):
        s = norm(s)
        if not s.startswith(("./", "../")):
            s = "./" + s
        return s
    is_changed = True
    previous = set()
    base = Path(base or '/').resolve()
    assert isinstance(name, str), f'pyjsbundler: detect_import_spec_type: resolve_aliases: name should be str, received {type(name)}'
    while is_changed:
        name_bkp_copy = name
        is_changed = False
        previous.add(name)
        for alias_mask, alias_replacement in aliases:
            alias_mask = norm(alias_mask)
            # path = resolve_import(base,name)
            # relative_path = path.relative_to(base)
            # relative_path = norm(relative_path)
            relative_path = name
            matching_groups = glob_to_groups(alias_mask)
            matching_groups_re = re.compile("^"+"".join([token.as_regex() for token in matching_groups]) + "$")
            matches = matching_groups_re.fullmatch(relative_path)
            if matches:
                # replacement_groups = [ v.value for v in glob_to_groups(alias_replacement) ]
                replacement_groups = glob_to_groups(alias_replacement)
                assert len(matching_groups) == len(replacement_groups), f'pyjsbundler: detect_import_spec_type: resolve_aliases: parsing glob strings failed, number of groups in alias_mask and alias_replacement does not match ({len(matching_groups)} !== {len(replacement_groups)}, alias_mask == {repr(alias_mask)}, alias_replacement == {repr(alias_replacement)})'
                result = ''
                for part_pattern, part_token_replacement in zip(matches.groups(), replacement_groups):
                    result += part_token_replacement.value if part_token_replacement.kind not in ('WILDCARD','INDEFINITE',) else part_pattern
                current_module_dir = (
                    Path(current_module_path).parent
                    if Path(current_module_path).is_file()
                    else Path(current_module_path)
                )
                name = norm_rel(os.path.relpath(base/result,current_module_dir))
                is_changed = name==name_bkp_copy
                if is_changed:
                    if name in previous:
                        raise Exception(f'pyjsbundler: detect_import_spec_type: resolve_aliases: circular replacement, changed from {repr(name_bkp_copy)} to {repr(name)} with {repr(alias_mask)} -> {repr(alias_replacement)} and got to previously processed {repr(previous.intersection(set([name])))}')
                    break
    return name



def classify_module_specifier(name) -> ModuleSpecifierType:
    # if name_matches_alias()
    if re.match(r'(\.|\.{2})/.*',name):
        return ModuleSpecifierType.PATH_RELATIVE
    elif re.match(r'\w+:.*',name):
        return ModuleSpecifierType.URL_ABSOLUTE
    elif re.match(r'/.*',name):
        return ModuleSpecifierType.PATH_ABSOLUTE
    else:
        return ModuleSpecifierType.BARE


def classify_module_specifier_role_for_bundler(name, base, current_module_path, aliases):
    specifier_resolved = resolve_aliases(name, base, current_module_path, aliases)
    type: ModuleSpecifierType = classify_module_specifier(specifier_resolved)
    if type in (ModuleSpecifierType.BARE,ModuleSpecifierType.URL_ABSOLUTE,):
        return ModuleSpecifierBundlerRole.UNTOUCH
    else:
        return ModuleSpecifierBundlerRole.PROCESS




