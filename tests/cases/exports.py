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
        ("generator_function", "export function* {n}() {{}}", "pass", ""),
        ("async_generator_function", "export async function* {n}() {{}}", "pass", ""),
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
        ("anonymous_function", "export default function() {}", "pass", ""),
        ("anonymous_async_function", "export default async function() {}", "pass", ""),
        ("generator_function", "export default function* aaa() {}", "pass", ""),
        ("async_generator_function", "export default async function* aaa() {}", "pass", ""),
        ("anonymous_generator_function", "export default function* () {}", "pass", ""),
        ("anonymous_async_generator_function", "export default async function* () {}", "pass", ""),
        ("class", "export default class Aaa {}", "pass", ""),
        ("anonymous_class", "export default class {}", "pass", ""),
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


def comment_variants():
    """Comments and other insignificant tokens inside ``export`` statements."""
    return [
        _case("comment_between_export_and_default", "export /* c */ default function aaa() {}", expected=("default",)),
        _case("comment_between_default_and_function", "export default /* c */ function aaa() {}", expected=("default",)),
        _case("comment_before_named_function", "export default function /* c */ aaa() {}", expected=("default",)),
        _case("comment_before_anonymous_function", "export default function /* c */ () {}", expected=("default",)),
        _case("line_comment_before_anonymous_function", "export default function // c\n() {}", expected=("default",)),
        _case("comment_before_anonymous_class", "export default class /* c */ {}", expected=("default",)),
        _case("comment_before_async_anonymous", "export default async /* c */ function () {}", expected=("default",)),
        _case("comment_in_named_declaration", "export function /* c */ aaa() {}", expected=("aaa",)),
        _case("comment_before_number_default", "export default /* c */ 42;", expected=("default",)),
        _case("comment_in_explicit_list", "const aaa = 1, bbb = 2; export { aaa, /* c */ bbb };", expected=("aaa", "bbb")),
    ]


EXPORT_CASES = named_declarations() + default_exports() + explicit_exports() + re_exports() + comment_variants()
