"""A small, lossless tokenizer for JavaScript source.

The tokenizer partitions a JavaScript source string into a flat list of tokens
whose ``value`` fields concatenate back to the original source exactly (it is
lossless).  It is intentionally small: the consumers only need to find
``import`` / ``export`` statements at the top level, so several constructs that
are hard to lex (template literals, regular expressions, strings, comments) are
treated as single opaque tokens.

Token kinds:

* ``SPACE``      — a run of horizontal whitespace (spaces, tabs, ...).
* ``NEWLINE``    — a single line terminator (``\\n``, ``\\r\\n``, ``\\r``, U+2028/9).
* ``COMMENT``    — a ``//`` line comment or ``/* ... */`` block comment.
* ``IDENT``      — an identifier or keyword.
* ``NUMBER``     — a numeric literal.
* ``STRING``     — a ``'...'`` or ``"..."`` string literal.
* ``TEMPLATE``   — a `` `...` `` template literal (``${...}`` handled recursively).
* ``REGEX``      — a ``/.../flags`` regular-expression literal.
* ``LBRACE``     — ``{``
* ``RBRACE``     — ``}``
* ``LPAREN``     — ``(``
* ``RPAREN``     — ``)``
* ``LBRACKET``   — ``[``
* ``RBRACKET``   — ``]``
* ``SEMICOLON``  — ``;``
* ``COMMA``      — ``,``
* ``DOT``        — ``.``
* ``COLON``      — ``:``
* ``OP``         — any other operator / punctuation (``+``, ``=>``, ``===``, ...).

Regular-expression vs. division is decided with the usual ECMAScript heuristic:
a ``/`` starts a regex literal when the previous significant token cannot end an
expression.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


class TokenizeError(Exception):
    """Raised when the source contains an unterminated construct."""


_LINE_TERMINATORS = "\r\n\u2028\u2029"

# Keywords after which a ``/`` starts a regular expression rather than division.
_KEYWORDS_BEFORE_REGEX = frozenset((
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "throw", "yield", "await", "case", "do", "else", "extends",
))

# Multi-character operators, longest first.
_OPERATORS = tuple(sorted((
    ">>>=", "===", "!==", "**=", "<<=", ">>=", "&&=", "||=", "??=",
    ">>>", "=>", "==", "!=", "<=", ">=", "&&", "||", "??", "?.",
    "**", "<<", ">>", "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "...",
), key=len, reverse=True))


def _is_ident_start(c):
    return c.isalpha() or c == "_" or c == "$"


def _is_ident_part(c):
    return c.isalnum() or c == "_" or c == "$"


class _Tokenizer:
    def __init__(self, src):
        self.src = src
        self.i = 0
        self.n = len(src)

    def run(self):
        tokens = []
        prev = None
        while self.i < self.n:
            token = self._scan_one(prev)
            tokens.append(token)
            if token.kind not in ("SPACE", "NEWLINE", "COMMENT"):
                prev = token
        return tokens

    def _error(self, message, offset):
        line = self.src.count("\n", 0, offset) + 1
        column = offset - self.src.rfind("\n", 0, offset)
        raise TokenizeError(f"{message} (at line {line}, column {column})")

    def _scan_one(self, prev):
        src = self.src
        i = self.i
        c = src[i]
        start = i

        # Line terminators.
        if c in _LINE_TERMINATORS:
            if c == "\r" and i + 1 < self.n and src[i + 1] == "\n":
                self.i += 2
            else:
                self.i += 1
            return Token("NEWLINE", src[start:self.i], start, self.i)

        # Horizontal whitespace run.
        if c.isspace():
            self.i += 1
            while self.i < self.n and src[self.i].isspace() and src[self.i] not in _LINE_TERMINATORS:
                self.i += 1
            return Token("SPACE", src[start:self.i], start, self.i)

        # Line comment.
        if src.startswith("//", i):
            self.i += 2
            while self.i < self.n and src[self.i] not in _LINE_TERMINATORS:
                self.i += 1
            return Token("COMMENT", src[start:self.i], start, self.i)

        # Block comment.
        if src.startswith("/*", i):
            self.i += 2
            while self.i < self.n - 1:
                if src[self.i:self.i + 2] == "*/":
                    self.i += 2
                    return Token("COMMENT", src[start:self.i], start, self.i)
                self.i += 1
            self._error("Unterminated block comment", start)

        # Quoted string literal.
        if c in "'\"":
            return self._scan_string()

        # Template literal.
        if c == "`":
            return self._scan_template()

        # Numeric literal.
        if c.isdigit() or (c == "." and i + 1 < self.n and src[i + 1].isdigit()):
            return self._scan_number()

        # Identifier / keyword.
        if _is_ident_start(c):
            self.i += 1
            while self.i < self.n and _is_ident_part(src[self.i]):
                self.i += 1
            return Token("IDENT", src[start:self.i], start, self.i)

        # Regular expression (vs. division).
        if c == "/" and self._starts_regex(prev):
            return self._scan_regex()

        # Multi-character operator.
        for op in _OPERATORS:
            if src.startswith(op, i):
                self.i += len(op)
                return Token("OP", op, start, self.i)

        # Single-character punctuation.
        self.i += 1
        kind = {
            "{": "LBRACE", "}": "RBRACE",
            "(": "LPAREN", ")": "RPAREN",
            "[": "LBRACKET", "]": "RBRACKET",
            ";": "SEMICOLON", ",": "COMMA", ".": "DOT", ":": "COLON",
        }.get(c, "OP")
        return Token(kind, c, start, self.i)

    def _scan_string(self):
        src = self.src
        start = self.i
        quote = src[self.i]
        self.i += 1
        while self.i < self.n:
            c = src[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == quote:
                self.i += 1
                return Token("STRING", src[start:self.i], start, self.i)
            if c in _LINE_TERMINATORS:
                self._error("Unterminated string literal", start)
            self.i += 1
        self._error("Unterminated string literal", start)

    def _scan_template(self):
        src = self.src
        start = self.i
        self.i += 1  # opening backtick
        while self.i < self.n:
            c = src[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "`":
                self.i += 1
                return Token("TEMPLATE", src[start:self.i], start, self.i)
            if c == "$" and self.i + 1 < self.n and src[self.i + 1] == "{":
                expression_start = self.i
                self.i += 2  # consume '${'
                self._skip_template_expression(expression_start)
                continue
            self.i += 1
        self._error("Unterminated template literal", start)

    def _skip_template_expression(self, start):
        """Skip from just after ``${`` to the matching closing ``}``."""
        depth = 0
        prev = None
        while self.i < self.n:
            token = self._scan_one(prev)
            if token.kind == "LBRACE":
                depth += 1
            elif token.kind == "RBRACE":
                depth -= 1
                if depth < 0:
                    return
            if token.kind not in ("SPACE", "NEWLINE", "COMMENT"):
                prev = token
        self._error("Unterminated template expression", start)

    def _scan_number(self):
        src = self.src
        start = self.i

        if src[self.i] == "0" and self.i + 1 < self.n and src[self.i + 1] in "xXbBoO":
            hex_digits = src[self.i + 1] in "xX"
            self.i += 2
            self._scan_digits(hex_digits=hex_digits)
            if self.i < self.n and src[self.i] == "n":
                self.i += 1
            return Token("NUMBER", src[start:self.i], start, self.i)

        self._scan_digits()
        if self.i < self.n and src[self.i] == ".":
            self.i += 1
            self._scan_digits()
        if self.i < self.n and src[self.i] in "eE":
            self.i += 1
            if self.i < self.n and src[self.i] in "+-":
                self.i += 1
            self._scan_digits()
        if self.i < self.n and src[self.i] == "n":
            self.i += 1
        return Token("NUMBER", src[start:self.i], start, self.i)

    def _scan_digits(self, hex_digits=False):
        while self.i < self.n:
            c = self.src[self.i]
            if c.isdigit() or c == "_" or (hex_digits and c.lower() in "abcdef"):
                self.i += 1
            else:
                break

    def _scan_regex(self):
        src = self.src
        start = self.i
        self.i += 1  # opening '/'
        in_class = False
        while self.i < self.n:
            c = src[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "[":
                in_class = True
                self.i += 1
                continue
            if c == "]" and in_class:
                in_class = False
                self.i += 1
                continue
            if c == "/" and not in_class:
                self.i += 1
                while self.i < self.n and src[self.i].isalpha():
                    self.i += 1
                return Token("REGEX", src[start:self.i], start, self.i)
            if c in _LINE_TERMINATORS:
                self._error("Unterminated regular expression literal", start)
            self.i += 1
        self._error("Unterminated regular expression literal", start)

    def _starts_regex(self, prev):
        if prev is None:
            return True
        kind = prev.kind
        value = prev.value
        if kind == "IDENT":
            return value in _KEYWORDS_BEFORE_REGEX
        if kind in ("NUMBER", "STRING", "TEMPLATE", "REGEX", "RPAREN", "RBRACKET", "RBRACE"):
            return False
        if kind in ("LPAREN", "LBRACKET", "LBRACE", "COMMA", "SEMICOLON", "COLON"):
            return True
        if kind == "OP":
            return value not in ("++", "--")
        return True


def process(src):
    """Tokenize ``src`` into a list of :class:`Token`."""
    return _Tokenizer(src).run()
