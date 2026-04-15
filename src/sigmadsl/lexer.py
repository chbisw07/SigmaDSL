from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag


class TokenKind(str, Enum):
    # structural
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    NEWLINE = "NEWLINE"
    EOF = "EOF"

    # identifiers / literals
    IDENT = "IDENT"
    STRING = "STRING"
    NUMBER = "NUMBER"
    PERCENT_NUMBER = "PERCENT_NUMBER"

    # keywords
    RULE = "RULE"
    IN = "IN"
    WHEN = "WHEN"
    THEN = "THEN"
    ELIF = "ELIF"
    ELSE = "ELSE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    TRUE = "TRUE"
    FALSE = "FALSE"

    # punctuation / operators
    COLON = ":"
    LPAREN = "("
    RPAREN = ")"
    COMMA = ","
    DOT = "."
    EQ = "="
    EQEQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"


KEYWORDS: dict[str, TokenKind] = {
    "rule": TokenKind.RULE,
    "in": TokenKind.IN,
    "when": TokenKind.WHEN,
    "then": TokenKind.THEN,
    "elif": TokenKind.ELIF,
    "else": TokenKind.ELSE,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
    "not": TokenKind.NOT,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str | None
    line: int
    column: int


def lex(source: str, *, file: Path | None = None) -> tuple[list[Token], list[Diagnostic]]:
    tokens: list[Token] = []
    diags: list[Diagnostic] = []

    indent_stack: list[int] = [0]

    def emit(kind: TokenKind, value: str | None, line: int, col: int):
        tokens.append(Token(kind=kind, value=value, line=line, column=col))

    def add_diag(code: str, message: str, line: int, col: int):
        diags.append(diag(code=code, message=message, file=file, line=line, column=col, severity=Severity.error))

    lines = source.splitlines()
    for line_no, raw in enumerate(lines, start=1):
        # Keep original; we compute indentation on the physical line.
        # Ignore blank lines and comment-only lines for indentation purposes.
        stripped = raw.lstrip(" ")
        if stripped == "" or stripped.startswith("#"):
            continue

        # Tabs in leading indentation are forbidden.
        leading = raw[: len(raw) - len(stripped)]
        if "\t" in leading:
            add_diag("SD101", "Tabs are not allowed for indentation", line_no, 1)
            # Treat as zero indentation to avoid cascading indentation noise.
            indent = 0
        else:
            indent = len(leading)

        current = indent_stack[-1]
        if indent > current:
            indent_stack.append(indent)
            emit(TokenKind.INDENT, None, line_no, 1)
        elif indent < current:
            while indent < indent_stack[-1]:
                indent_stack.pop()
                emit(TokenKind.DEDENT, None, line_no, 1)
            if indent != indent_stack[-1]:
                add_diag("SD101", "Inconsistent indentation (does not match any prior block)", line_no, 1)

        i = indent
        col = indent + 1
        in_string = False

        def peek(offset: int = 0) -> str:
            j = i + offset
            if j >= len(raw):
                return ""
            return raw[j]

        while i < len(raw):
            ch = raw[i]

            # Whitespace
            if ch in " \r":
                i += 1
                col += 1
                continue

            # Comment (only outside strings)
            if ch == "#":
                break

            # String literal (double-quoted)
            if ch == '"':
                start_col = col
                i += 1
                col += 1
                buf: list[str] = []
                while i < len(raw):
                    c = raw[i]
                    if c == "\\":
                        if i + 1 >= len(raw):
                            break
                        buf.append(raw[i + 1])
                        i += 2
                        col += 2
                        continue
                    if c == '"':
                        i += 1
                        col += 1
                        emit(TokenKind.STRING, "".join(buf), line_no, start_col)
                        break
                    buf.append(c)
                    i += 1
                    col += 1
                else:
                    add_diag("SD203", "Unterminated string literal", line_no, start_col)
                # If loop ended via unterminated string, we stop scanning this line to avoid noise.
                if i >= len(raw) or raw[i - 1] != '"':
                    break
                continue

            # Ident / keyword
            if ch.isalpha() or ch == "_":
                start = i
                start_col = col
                i += 1
                col += 1
                while i < len(raw) and (raw[i].isalnum() or raw[i] == "_"):
                    i += 1
                    col += 1
                text = raw[start:i]
                kind = KEYWORDS.get(text, TokenKind.IDENT)
                emit(kind, text if kind == TokenKind.IDENT else None, line_no, start_col)
                continue

            # Number / decimal / percent number
            if ch.isdigit():
                start = i
                start_col = col
                has_dot = False
                i += 1
                col += 1
                while i < len(raw):
                    c = raw[i]
                    if c == "." and not has_dot and (i + 1 < len(raw) and raw[i + 1].isdigit()):
                        has_dot = True
                        i += 1
                        col += 1
                        continue
                    if c.isdigit():
                        i += 1
                        col += 1
                        continue
                    break
                num = raw[start:i]
                if i < len(raw) and raw[i] == "%":
                    emit(TokenKind.PERCENT_NUMBER, num, line_no, start_col)
                    i += 1
                    col += 1
                else:
                    emit(TokenKind.NUMBER, num, line_no, start_col)
                continue

            # Two-character operators
            two = raw[i : i + 2]
            if two in ("==", "!=", "<=", ">="):
                kind = {
                    "==": TokenKind.EQEQ,
                    "!=": TokenKind.NE,
                    "<=": TokenKind.LE,
                    ">=": TokenKind.GE,
                }[two]
                emit(kind, None, line_no, col)
                i += 2
                col += 2
                continue

            # Single-character tokens
            single_map = {
                ":": TokenKind.COLON,
                "(": TokenKind.LPAREN,
                ")": TokenKind.RPAREN,
                ",": TokenKind.COMMA,
                ".": TokenKind.DOT,
                "=": TokenKind.EQ,
                "<": TokenKind.LT,
                ">": TokenKind.GT,
                "+": TokenKind.PLUS,
                "-": TokenKind.MINUS,
                "*": TokenKind.STAR,
                "/": TokenKind.SLASH,
            }
            if ch in single_map:
                emit(single_map[ch], None, line_no, col)
                i += 1
                col += 1
                continue

            add_diag("SD100", f"Unexpected character: {ch!r}", line_no, col)
            i += 1
            col += 1

        emit(TokenKind.NEWLINE, None, line_no, len(raw) + 1)

    # Close any remaining indentation
    if len(indent_stack) > 1:
        while len(indent_stack) > 1:
            indent_stack.pop()
            emit(TokenKind.DEDENT, None, len(lines) + 1, 1)

    emit(TokenKind.EOF, None, len(lines) + 1, 1)
    return tokens, diags

