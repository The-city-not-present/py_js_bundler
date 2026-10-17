"""Data + generators for ``export``-statement test cases.

Cases are produced by small generator functions and then concatenated, so new
variants are added by extending the tables below rather than copy-pasting test
functions.
"""

from ..helpers import ExportCase


def _case(cid, source, *, expected=(), status="pass", reason="", strip=True):
    return ExportCase(
        id=cid,
        source=source,
        status=status,
        reason=reason,
        expected_keys=expected,
        strip_export=strip,
    )


def named_declarations():
    """``export function/class/const/... name`` variants."""
    templates = [
        ("function", "export function {n}() {{}}", "pass", ""),
        ("async_function", "export async function {n}() {{}}", "pass", ""),
        ("generator_function", "export function* {n}() {{}}", "xfail", "generator functions not supported"),
        ("async_generator_function", "export async function* {n}() {{}}", "xfail", "async generator functions not supported"),
        ("class", "export class {n} {{}}", "pass", ""),
        ("const", "export const {n} = 1;", "pass", ""),
        ("const_arrow", "export const {n} = () => {{}};", "pass", ""),
        ("let", "export let {n} = 1;", "pass", ""),
        ("var", "export var {n} = 1;", "pass", ""),
    ]
    cases = []
    for cid, template, status, reason in templates:
        name = "Aaa" if cid == "class" else "aaa"
        cases.append(
            _case(
                f"named_{cid}",
                template.format(n=name),
                expected=(name,),
                status=status,
                reason=reason,
            )
        )
    # Multiple declarators in one ``const``: only the first is currently exported.
    cases.append(
        _case(
            "named_const_multiple_declarators",
            "export const aaa = 1, bbb = 2;",
            expected=("aaa", "bbb"),
            status="xfail",
            reason="only the first declarator is exported",
        )
    )
    return cases


def default_exports():
    """``export default ...`` variants."""
    templates = [
        ("function", "export default function aaa() {}", "pass", ""),
        ("async_function", "export default async function aaa() {}", "pass", ""),
        ("anonymous_function", "export default function() {}", "xfail", "anonymous default function not supported"),
        ("anonymous_async_function", "export default async function() {}", "xfail", "anonymous default async function not supported"),
        ("generator_function", "export default function* aaa() {}", "xfail", "generator default function not supported"),
        ("class", "export default class Aaa {}", "pass", ""),
        ("anonymous_class", "export default class {}", "xfail", "anonymous default class not supported"),
        ("identifier_after_function", "function aaa() {}; export default aaa;", "pass", ""),
        ("identifier_after_const", "const aaa = 1; export default aaa;", "pass", ""),
        ("numeric_literal", "export default 42;", "pass", ""),
        ("object_literal", "export default { a: 1 };", "xfail", "object literal default not supported"),
        ("array_literal", "export default [1, 2];", "xfail", "array literal default not supported"),
        ("parenthesized_expression", "export default (42);", "xfail", "parenthesized default expression not supported"),
    ]
    return [
        _case(f"default_{cid}", source, expected=("default",), status=status, reason=reason)
        for cid, source, status, reason in templates
    ]


def explicit_exports():
    """``export { ... }`` variants (explicit export lists)."""
    templates = [
        ("single", "const aaa = 1; export { aaa };", ("aaa",)),
        ("multiple", "const aaa = 1, bbb = 2; export { aaa, bbb };", ("aaa", "bbb")),
        ("aliased", "const aaa = 1; export { aaa as bbb };", ("bbb",)),
        ("aliased_default", "const aaa = 1; export { aaa as default };", ("default",)),
    ]
    return [
        _case(f"explicit_{cid}", source, expected=expected)
        for cid, source, expected in templates
    ]


def re_exports():
    """``export ... from './module'`` variants (re-exports)."""
    templates = [
        ("star", 'export * from "./lib";'),
        ("star_as_namespace", 'export * as ns from "./lib";'),
        ("named", 'export { aaa } from "./lib";'),
        ("named_aliased", 'export { aaa as bbb } from "./lib";'),
        ("named_multiple", 'export { aaa, bbb } from "./lib";'),
    ]
    return [
        _case(f"reexport_{cid}", source, status="xfail", reason="re-exports not supported")
        for cid, source in templates
    ]


EXPORT_CASES = named_declarations() + default_exports() + explicit_exports() + re_exports()
