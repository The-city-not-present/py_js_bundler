"""Data for the JavaScript tokenizer tests."""

from ..helpers import TokenizeCase


def _case(cid, source, expected=(), error=False):
    return TokenizeCase(id=cid, source=source, expected=expected, error=error)


TOKENIZE_CASES = [
    # --- trivial / empty ---
    _case("empty", ""),

    # --- identifiers & numbers ---
    _case("ident", "foo", expected=(("IDENT", "foo"),)),
    _case("keyword_export", "export", expected=(("IDENT", "export"),)),
    _case("keyword_import", "import", expected=(("IDENT", "import"),)),
    _case("ident_unicode", "café", expected=(("IDENT", "café"),)),
    _case("number_int", "42", expected=(("NUMBER", "42"),)),
    _case("number_float", "3.14", expected=(("NUMBER", "3.14"),)),
    _case("number_leading_dot", ".5", expected=(("NUMBER", ".5"),)),
    _case("number_hex", "0x1F", expected=(("NUMBER", "0x1F"),)),
    _case("number_binary", "0b101", expected=(("NUMBER", "0b101"),)),
    _case("number_exponent", "1e3", expected=(("NUMBER", "1e3"),)),
    _case("number_bigint", "10n", expected=(("NUMBER", "10n"),)),

    # --- punctuation ---
    _case("semicolon", ";", expected=(("SEMICOLON", ";"),)),
    _case("braces", "{}", expected=(("LBRACE", "{"), ("RBRACE", "}"))),
    _case("parens", "()", expected=(("LPAREN", "("), ("RPAREN", ")"))),
    _case("brackets", "[]", expected=(("LBRACKET", "["), ("RBRACKET", "]"))),
    _case("comma", ",", expected=(("COMMA", ","),)),
    _case("dot", ".", expected=(("DOT", "."),)),
    _case("colon", ":", expected=(("COLON", ":"),)),

    # --- operators ---
    _case("op_arrow", "=>", expected=(("OP", "=>"),)),
    _case("op_strict_eq", "===", expected=(("OP", "==="),)),
    _case("op_spread", "...", expected=(("OP", "..."),)),
    _case("op_optional_chain", "?.", expected=(("OP", "?."),)),
    _case("op_compound_div", "a /= b", expected=(("IDENT", "a"), ("SPACE", " "), ("OP", "/="), ("SPACE", " "), ("IDENT", "b"))),
    _case("postfix_incr", "a++", expected=(("IDENT", "a"), ("OP", "++"))),
    _case("postfix_decr", "a--", expected=(("IDENT", "a"), ("OP", "--"))),

    # --- whitespace / newlines ---
    _case("space_run", "  \t ", expected=(("SPACE", "  \t "),)),
    _case("newline", "\n", expected=(("NEWLINE", "\n"),)),
    _case("crlf", "\r\n", expected=(("NEWLINE", "\r\n"),)),
    _case("id_newline_id", "a\nb", expected=(("IDENT", "a"), ("NEWLINE", "\n"), ("IDENT", "b"))),
    _case("id_spaces_id", "a  b", expected=(("IDENT", "a"), ("SPACE", "  "), ("IDENT", "b"))),

    # --- comments ---
    _case("line_comment", "// hi\n", expected=(("COMMENT", "// hi"), ("NEWLINE", "\n"))),
    _case("block_comment", "/* hi */", expected=(("COMMENT", "/* hi */"),)),
    _case("comment_between_idents", "a /* x */ b", expected=(("IDENT", "a"), ("SPACE", " "), ("COMMENT", "/* x */"), ("SPACE", " "), ("IDENT", "b"))),

    # --- strings ---
    _case("string_single", "'hi'", expected=(("STRING", "'hi'"),)),
    _case("string_double", '"hi"', expected=(("STRING", '"hi"'),)),
    _case("string_escaped_quote", r"'it\'s'", expected=(("STRING", r"'it\'s'"),)),
    _case("string_with_braces", '"a{b}"', expected=(("STRING", '"a{b}"'),)),

    # --- template literals ---
    _case("template_plain", "`hi`", expected=(("TEMPLATE", "`hi`"),)),
    _case("template_expr", "`a ${b} c`", expected=(("TEMPLATE", "`a ${b} c`"),)),
    _case("template_nested_braces", "`a ${{x: 1}} c`", expected=(("TEMPLATE", "`a ${{x: 1}} c`"),)),
    _case("template_nested_template", "`a ${`nested`} c`", expected=(("TEMPLATE", "`a ${`nested`} c`"),)),
    _case("template_string_in_expr", "`a ${'}'} c`", expected=(("TEMPLATE", "`a ${'}'} c`"),)),
    _case("template_regex_in_expr", "`a ${/}/} c`", expected=(("TEMPLATE", "`a ${/}/} c`"),)),
    _case("template_escaped_interp", r"`a \${b} c`", expected=(("TEMPLATE", r"`a \${b} c`"),)),
    _case("template_escaped_backtick", r"`a \` c`", expected=(("TEMPLATE", r"`a \` c`"),)),
    _case("template_assignment", "const t = `x`;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "t"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("TEMPLATE", "`x`"), ("SEMICOLON", ";"))),

    # --- regular expressions vs division ---
    _case("regex_assignment", "const r = /abc/;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "r"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("REGEX", "/abc/"), ("SEMICOLON", ";"))),
    _case("regex_escaped_slash", r"const r = /a\/b/gi;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "r"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("REGEX", r"/a\/b/gi"), ("SEMICOLON", ";"))),
    _case("regex_char_class_braces", "const r = /[{}]/;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "r"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("REGEX", "/[{}]/"), ("SEMICOLON", ";"))),
    _case("division", "a / b / c;", expected=(("IDENT", "a"), ("SPACE", " "), ("OP", "/"), ("SPACE", " "), ("IDENT", "b"), ("SPACE", " "), ("OP", "/"), ("SPACE", " "), ("IDENT", "c"), ("SEMICOLON", ";"))),
    _case("regex_method", "x = /re/.test(y);", expected=(("IDENT", "x"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("REGEX", "/re/"), ("DOT", "."), ("IDENT", "test"), ("LPAREN", "("), ("IDENT", "y"), ("RPAREN", ")"), ("SEMICOLON", ";"))),
    _case("regex_after_return", "return /re/;", expected=(("IDENT", "return"), ("SPACE", " "), ("REGEX", "/re/"), ("SEMICOLON", ";"))),
    _case("regex_after_typeof", "typeof /re/;", expected=(("IDENT", "typeof"), ("SPACE", " "), ("REGEX", "/re/"), ("SEMICOLON", ";"))),

    # --- import/export keywords inside opaque constructs must not leak ---
    _case("import_in_string", 'const s = "import x";', expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "s"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("STRING", '"import x"'), ("SEMICOLON", ";"))),
    _case("export_in_template", "const t = `export default 1`;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "t"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("TEMPLATE", "`export default 1`"), ("SEMICOLON", ";"))),
    _case("import_in_comment", "// import x\nconst a = 1;", expected=(("COMMENT", "// import x"), ("NEWLINE", "\n"), ("IDENT", "const"), ("SPACE", " "), ("IDENT", "a"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("NUMBER", "1"), ("SEMICOLON", ";"))),
    _case("import_in_regex", "const r = /import/;", expected=(("IDENT", "const"), ("SPACE", " "), ("IDENT", "r"), ("SPACE", " "), ("OP", "="), ("SPACE", " "), ("REGEX", "/import/"), ("SEMICOLON", ";"))),

    # --- unterminated constructs ---
    _case("unterminated_single_string", "'abc", error=True),
    _case("unterminated_double_string", '"abc', error=True),
    _case("unterminated_template", "`abc", error=True),
    _case("unterminated_template_expr", "`a ${b}", error=True),
    _case("unterminated_block_comment", "/* unterminated", error=True),
    _case("unterminated_regex", "/abc", error=True),
]
