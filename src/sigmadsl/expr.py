from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ast import SourceSpan
from .diagnostics import Diagnostic, Severity, diag
from .lexer import Token, TokenKind


@dataclass(frozen=True)
class ExprNode:
    span: SourceSpan


@dataclass(frozen=True)
class BoolLiteral(ExprNode):
    value: bool


@dataclass(frozen=True)
class StringLiteral(ExprNode):
    value: str


@dataclass(frozen=True)
class IntLiteral(ExprNode):
    raw: str


@dataclass(frozen=True)
class DecimalLiteral(ExprNode):
    raw: str


@dataclass(frozen=True)
class PercentLiteral(ExprNode):
    raw: str


@dataclass(frozen=True)
class Name(ExprNode):
    value: str


@dataclass(frozen=True)
class Attribute(ExprNode):
    base: ExprNode
    attr: str


@dataclass(frozen=True)
class Call(ExprNode):
    func: ExprNode
    args: tuple[ExprNode, ...]
    kwargs: tuple[tuple[str, ExprNode], ...]


@dataclass(frozen=True)
class UnaryOp(ExprNode):
    op: str
    operand: ExprNode


@dataclass(frozen=True)
class BinaryOp(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode


@dataclass(frozen=True)
class CompareOp(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode


class _ExprCursor:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self, k: int = 0) -> Token:
        j = self.i + k
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def advance(self) -> Token:
        t = self.peek()
        self.i = min(self.i + 1, len(self.tokens) - 1)
        return t

    def match(self, kind: TokenKind) -> bool:
        if self.peek().kind == kind:
            self.advance()
            return True
        return False


def parse_expression_tokens(
    tokens: list[Token],
    *,
    file: Path | None = None,
) -> tuple[ExprNode | None, list[Diagnostic]]:
    """
    Parse an expression from a token slice (no NEWLINE/INDENT/DEDENT).

    Sprint 0.2-A: This is used for type checking and better diagnostics.
    """

    if not tokens:
        return None, []

    # Add a sentinel EOF-like token for safe peeking.
    last = tokens[-1]
    eof = Token(kind=TokenKind.EOF, value=None, line=last.line, column=last.column + 1)
    cur = _ExprCursor(tokens=tokens + [eof])
    diags: list[Diagnostic] = []

    def add(code: str, message: str, t: Token):
        diags.append(diag(code=code, message=message, file=file, line=t.line, column=t.column, severity=Severity.error))

    def span_of(t: Token) -> SourceSpan:
        return SourceSpan(line=t.line, column=t.column)

    def token_text(t: Token) -> str:
        if t.kind == TokenKind.IDENT:
            return t.value or ""
        if t.kind == TokenKind.STRING:
            return '"' + (t.value or "") + '"'
        if t.kind == TokenKind.NUMBER:
            return t.value or ""
        if t.kind == TokenKind.PERCENT_NUMBER:
            return (t.value or "") + "%"
        if t.kind in (TokenKind.AND, TokenKind.OR, TokenKind.NOT, TokenKind.TRUE, TokenKind.FALSE):
            return t.kind.value.lower()
        return t.kind.value

    def lbp(kind: TokenKind) -> int:
        return {
            TokenKind.OR: 10,
            TokenKind.AND: 20,
            TokenKind.EQEQ: 30,
            TokenKind.NE: 30,
            TokenKind.LT: 30,
            TokenKind.LE: 30,
            TokenKind.GT: 30,
            TokenKind.GE: 30,
            TokenKind.PLUS: 40,
            TokenKind.MINUS: 40,
            TokenKind.STAR: 50,
            TokenKind.SLASH: 50,
            TokenKind.DOT: 80,
            TokenKind.LPAREN: 80,
        }.get(kind, 0)

    def parse_primary() -> ExprNode | None:
        t = cur.peek()

        if t.kind == TokenKind.TRUE:
            cur.advance()
            return BoolLiteral(span=span_of(t), value=True)
        if t.kind == TokenKind.FALSE:
            cur.advance()
            return BoolLiteral(span=span_of(t), value=False)
        if t.kind == TokenKind.STRING:
            cur.advance()
            return StringLiteral(span=span_of(t), value=t.value or "")
        if t.kind == TokenKind.NUMBER:
            cur.advance()
            raw = t.value or ""
            if "." in raw:
                return DecimalLiteral(span=span_of(t), raw=raw)
            return IntLiteral(span=span_of(t), raw=raw)
        if t.kind == TokenKind.PERCENT_NUMBER:
            cur.advance()
            return PercentLiteral(span=span_of(t), raw=t.value or "")
        if t.kind == TokenKind.IDENT:
            cur.advance()
            return Name(span=span_of(t), value=t.value or "")
        if t.kind == TokenKind.LPAREN:
            cur.advance()
            inner = parse_expr(0)
            if not cur.match(TokenKind.RPAREN):
                add("SD200", "Expected ')'", cur.peek())
            return inner

        add("SD200", f"Unexpected token in expression: {token_text(t)!r}", t)
        cur.advance()
        return None

    def parse_postfix(left: ExprNode) -> ExprNode:
        while True:
            t = cur.peek()
            if t.kind == TokenKind.DOT:
                cur.advance()
                name_tok = cur.peek()
                if name_tok.kind != TokenKind.IDENT:
                    add("SD200", "Expected identifier after '.'", name_tok)
                    return left
                cur.advance()
                left = Attribute(span=span_of(t), base=left, attr=name_tok.value or "")
                continue
            if t.kind == TokenKind.LPAREN:
                lparen = cur.advance()
                args: list[ExprNode] = []
                kwargs: list[tuple[str, ExprNode]] = []
                if cur.peek().kind != TokenKind.RPAREN:
                    while True:
                        # keyword arg: IDENT '=' expr
                        if cur.peek().kind == TokenKind.IDENT and cur.peek(1).kind == TokenKind.EQ:
                            key_tok = cur.advance()
                            cur.advance()  # '='
                            val = parse_expr(0)
                            if val is not None:
                                kwargs.append((key_tok.value or "", val))
                        else:
                            val = parse_expr(0)
                            if val is not None:
                                args.append(val)
                        if cur.match(TokenKind.COMMA):
                            continue
                        break
                if not cur.match(TokenKind.RPAREN):
                    add("SD200", "Expected ')'", cur.peek())
                left = Call(span=span_of(lparen), func=left, args=tuple(args), kwargs=tuple(kwargs))
                continue
            break
        return left

    def parse_prefix() -> ExprNode | None:
        t = cur.peek()
        if t.kind == TokenKind.NOT:
            cur.advance()
            operand = parse_expr(60)
            if operand is None:
                return None
            return UnaryOp(span=span_of(t), op="not", operand=operand)
        if t.kind == TokenKind.PLUS:
            cur.advance()
            operand = parse_expr(60)
            if operand is None:
                return None
            return UnaryOp(span=span_of(t), op="+", operand=operand)
        if t.kind == TokenKind.MINUS:
            cur.advance()
            operand = parse_expr(60)
            if operand is None:
                return None
            return UnaryOp(span=span_of(t), op="-", operand=operand)
        return parse_primary()

    def parse_infix(left: ExprNode, op_tok: Token) -> ExprNode | None:
        op_kind = op_tok.kind
        op_text = token_text(op_tok)

        if op_kind in (TokenKind.EQEQ, TokenKind.NE, TokenKind.LT, TokenKind.LE, TokenKind.GT, TokenKind.GE):
            right = parse_expr(31)
            if right is None:
                return None
            return CompareOp(span=span_of(op_tok), op=op_text, left=left, right=right)

        right = parse_expr(lbp(op_kind) + 1)
        if right is None:
            return None
        return BinaryOp(span=span_of(op_tok), op=op_text, left=left, right=right)

    def parse_expr(min_bp: int) -> ExprNode | None:
        left = parse_prefix()
        if left is None:
            return None
        left = parse_postfix(left)

        while True:
            t = cur.peek()
            if t.kind in (TokenKind.EOF, TokenKind.RPAREN, TokenKind.COMMA):
                break
            bp = lbp(t.kind)
            if bp < min_bp:
                break
            # comparisons are non-chainable in v0.2 (avoid Python semantics surprises)
            if isinstance(left, CompareOp) and t.kind in (
                TokenKind.EQEQ,
                TokenKind.NE,
                TokenKind.LT,
                TokenKind.LE,
                TokenKind.GT,
                TokenKind.GE,
            ):
                add("SD200", "Chained comparisons are not supported (use 'and')", t)
                break

            op_tok = cur.advance()
            left2 = parse_infix(left, op_tok)
            if left2 is None:
                return left
            left = parse_postfix(left2)

        return left

    expr = parse_expr(0)
    if expr is None:
        return None, diags

    # If anything remains (besides EOF), it's an error.
    if cur.peek().kind != TokenKind.EOF:
        add("SD200", f"Unexpected token after expression: {token_text(cur.peek())!r}", cur.peek())

    return expr, diags


def dotted_name(expr: ExprNode) -> str | None:
    """
    If expr is a Name or dotted Attribute chain, return the dotted string.
    """

    if isinstance(expr, Name):
        return expr.value
    if isinstance(expr, Attribute):
        base = dotted_name(expr.base)
        if base is None:
            return None
        return f"{base}.{expr.attr}"
    return None

