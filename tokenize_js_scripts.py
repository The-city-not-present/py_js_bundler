from dataclasses import dataclass

@dataclass
class Token:
    kind: str
    value: str


def process(src):
    tokens = []
    i = 0
    n = len(src)

    while i < n:
        c = src[i]

        # whitespace-linebreak
        if c=='\n':
            tokens.append(Token("SPACEBR", src[i:i+1]))
            i += 1
            continue

        # whitespace
        if c.isspace():
            start = i
            while i < n and src[i].isspace() and not(c=='\n'):
                i += 1
            tokens.append(Token("SPACE", src[start:i]))
            continue

        # line comment
        if src.startswith("//", i):
            start = i
            i += 2
            while i < n and src[i] != "\n":
                i += 1
            tokens.append(Token("COMMENT", src[start:i]))
            continue

        # block comment
        if src.startswith("/*", i):
            start = i
            i += 2
            while i < n - 1 and src[i:i+2] != "*/":
                i += 1
            i += 2
            tokens.append(Token("COMMENT", src[start:i]))
            continue

        # strings
        if c in "'\"`":
            quote = c
            start = i
            i += 1

            while i < n:
                if src[i] == "\\":
                    i += 2
                elif src[i] == quote:
                    i += 1
                    break
                else:
                    i += 1

            tokens.append(Token("STRING", src[start:i]))
            continue

        # identifier
        if c.isalpha() or c in "_$":
            start = i
            i += 1

            while i < n and (src[i].isalnum() or src[i] in "_$"):
                i += 1

            tokens.append(Token("IDENT", src[start:i]))
            continue

        # identifier
        if c.isdigit():
            start = i
            i += 1

            while i < n and (src[i].isdigit()):
                i += 1

            tokens.append(Token("NUM", src[start:i]))
            continue

        # punctuation
        if c in "{}(),;.*":
            tokens.append(Token("PUNCT", c))
            i += 1
            continue

        # everything else
        tokens.append(Token("OTHER", c))
        i += 1

    return tokens
