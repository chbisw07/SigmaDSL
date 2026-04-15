from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ast
from .diagnostics import Diagnostic, Severity, diag
from .expr import parse_expression_tokens
from .lexer import Token, TokenKind, lex


FORBIDDEN_STMT_STARTERS = {"for", "while", "def", "import", "from"}


@dataclass
class _Cursor:
    tokens: list[Token]
    i: int = 0

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


def parse_source(source: str, *, file: Path | None = None) -> tuple[ast.SourceFile | None, list[Diagnostic]]:
    tokens, diags = lex(source, file=file)
    cur = _Cursor(tokens=tokens)

    def add(code: str, message: str, t: Token, severity: Severity = Severity.error):
        diags.append(
            diag(
                code=code,
                message=message,
                file=file,
                line=t.line,
                column=t.column,
                severity=severity,
            )
        )

    def expect(kind: TokenKind, code: str, message: str) -> Token:
        t = cur.peek()
        if t.kind == kind:
            return cur.advance()
        add(code, message, t)
        return t

    def skip_to_line_end():
        while cur.peek().kind not in (TokenKind.NEWLINE, TokenKind.EOF):
            cur.advance()
        cur.match(TokenKind.NEWLINE)

    def consume_newlines():
        while cur.match(TokenKind.NEWLINE):
            pass

    def parse_rule_name() -> tuple[str | None, Token]:
        t = cur.peek()
        if t.kind == TokenKind.STRING:
            cur.advance()
            return (t.value or "", t)
        if t.kind == TokenKind.IDENT:
            cur.advance()
            return (t.value or "", t)
        add("SD200", "Expected rule name (string or identifier)", t)
        return (None, t)

    def parse_context() -> tuple[str | None, Token]:
        t = cur.peek()
        if t.kind == TokenKind.IDENT:
            cur.advance()
            return (t.value or "", t)
        add("SD200", "Expected context identifier after 'in'", t)
        return (None, t)

    def parse_expr_until(stop_kinds: set[TokenKind], *, allow_eq: bool) -> ast.Expr:
        start = cur.peek()
        depth = 0
        parts: list[str] = []
        expr_tokens: list[Token] = []

        def tok_text(tok: Token) -> str:
            if tok.kind == TokenKind.IDENT:
                return tok.value or ""
            if tok.kind == TokenKind.STRING:
                return '"' + (tok.value or "") + '"'
            if tok.kind in (TokenKind.NUMBER, TokenKind.PERCENT_NUMBER):
                return (tok.value or "") + ("%" if tok.kind == TokenKind.PERCENT_NUMBER else "")
            # Operators/punct: use the kind value for single-char, or mapping for multi
            if tok.kind in (
                TokenKind.COLON,
                TokenKind.LPAREN,
                TokenKind.RPAREN,
                TokenKind.COMMA,
                TokenKind.DOT,
                TokenKind.EQ,
                TokenKind.EQEQ,
                TokenKind.NE,
                TokenKind.LT,
                TokenKind.GT,
                TokenKind.LE,
                TokenKind.GE,
                TokenKind.PLUS,
                TokenKind.MINUS,
                TokenKind.STAR,
                TokenKind.SLASH,
            ):
                return tok.kind.value
            if tok.kind in (
                TokenKind.AND,
                TokenKind.OR,
                TokenKind.NOT,
                TokenKind.TRUE,
                TokenKind.FALSE,
            ):
                return tok.kind.value.lower()
            return ""

        while True:
            t = cur.peek()
            if t.kind in stop_kinds or t.kind in (TokenKind.NEWLINE, TokenKind.EOF):
                break
            if t.kind == TokenKind.EQ and not allow_eq:
                add("SD204", "Assignments are not allowed in SigmaDSL expressions (use '==')", t)
            if t.kind == TokenKind.LPAREN:
                depth += 1
            elif t.kind == TokenKind.RPAREN:
                depth -= 1
                if depth < 0:
                    add("SD200", "Unmatched ')'", t)
                    depth = 0
            parts.append(tok_text(t))
            expr_tokens.append(t)
            cur.advance()

        if depth != 0:
            add("SD200", "Unbalanced parentheses in expression", start)

        text = " ".join(p for p in parts if p)
        node, expr_diags = parse_expression_tokens(expr_tokens, file=file)
        diags.extend(expr_diags)
        return ast.Expr(text=text, node=node, span=ast.SourceSpan(line=start.line, column=start.column))

    def parse_verb_call() -> ast.VerbCall | None:
        name_tok = cur.peek()
        if name_tok.kind != TokenKind.IDENT:
            add("SD200", "Expected verb name identifier after 'then'", name_tok)
            return None
        name = name_tok.value or ""
        cur.advance()

        expect(TokenKind.LPAREN, "SD200", "Expected '(' after verb name")

        args: list[ast.VerbArg] = []
        if cur.peek().kind != TokenKind.RPAREN:
            while True:
                arg_name_tok = cur.peek()
                if arg_name_tok.kind != TokenKind.IDENT:
                    add("SD200", "Expected argument name identifier", arg_name_tok)
                    break
                arg_name = arg_name_tok.value or ""
                cur.advance()
                expect(TokenKind.EQ, "SD200", "Expected '=' after argument name")
                value = parse_expr_until({TokenKind.COMMA, TokenKind.RPAREN}, allow_eq=False)
                args.append(ast.VerbArg(name=arg_name, value=value))
                if cur.match(TokenKind.COMMA):
                    continue
                break

        expect(TokenKind.RPAREN, "SD200", "Expected ')' to close verb call")
        return ast.VerbCall(
            name=name,
            args=tuple(args),
            span=ast.SourceSpan(line=name_tok.line, column=name_tok.column),
        )

    def parse_then_lines() -> list[ast.ThenLine]:
        actions: list[ast.ThenLine] = []
        while True:
            consume_newlines()
            t = cur.peek()
            if t.kind == TokenKind.DEDENT or t.kind == TokenKind.EOF:
                break
            if t.kind != TokenKind.THEN:
                # Extra helpful diagnostics for forbidden statement starters / assignments.
                if t.kind == TokenKind.IDENT and (t.value or "") in FORBIDDEN_STMT_STARTERS:
                    add("SD204", f"Forbidden construct in SigmaDSL: {t.value!r}", t)
                elif t.kind == TokenKind.IDENT and cur.peek(1).kind == TokenKind.EQ:
                    add("SD204", "Assignments are not allowed in SigmaDSL (use verb calls under 'then')", t)
                else:
                    add("SD200", "Expected 'then' line inside branch", t)
                skip_to_line_end()
                continue

            then_tok = cur.advance()
            call = parse_verb_call()
            expect(TokenKind.NEWLINE, "SD200", "Expected end of line after 'then' verb call")
            if call is None:
                continue
            actions.append(ast.ThenLine(call=call, span=ast.SourceSpan(line=then_tok.line, column=then_tok.column)))
        return actions

    def parse_branch(kind: TokenKind) -> ast.Branch | None:
        head = cur.advance()  # when/elif/else
        cond: ast.Expr | None = None
        if kind in (TokenKind.WHEN, TokenKind.ELIF):
            cond = parse_expr_until({TokenKind.COLON}, allow_eq=False)
        expect(TokenKind.COLON, "SD200", "Expected ':' after branch header")
        expect(TokenKind.NEWLINE, "SD200", "Expected newline after branch header")
        expect(TokenKind.INDENT, "SD101", "Expected indented block under branch")

        actions = parse_then_lines()
        if not actions:
            add("SD201", "Branch must contain at least one 'then' line", head)
        expect(TokenKind.DEDENT, "SD101", "Expected end of indented branch block")

        kind_s = {
            TokenKind.WHEN: "when",
            TokenKind.ELIF: "elif",
            TokenKind.ELSE: "else",
        }[kind]
        return ast.Branch(
            kind=kind_s,
            condition=cond,
            actions=tuple(actions),
            span=ast.SourceSpan(line=head.line, column=head.column),
        )

    def parse_rule_block() -> ast.Rule | None:
        rule_tok = cur.advance()  # 'rule'
        name, name_tok = parse_rule_name()

        if not cur.match(TokenKind.IN):
            add("SD200", "Expected 'in' after rule name", cur.peek())
        context, ctx_tok = parse_context()

        expect(TokenKind.COLON, "SD200", "Expected ':' after rule header")
        expect(TokenKind.NEWLINE, "SD200", "Expected newline after rule header")
        expect(TokenKind.INDENT, "SD101", "Expected indented rule body")

        branches: list[ast.Branch] = []
        consume_newlines()

        if cur.peek().kind != TokenKind.WHEN:
            add("SD201", "Rule must start with a 'when' branch", cur.peek())
        else:
            b = parse_branch(TokenKind.WHEN)
            if b:
                branches.append(b)

            while cur.peek().kind == TokenKind.ELIF:
                bb = parse_branch(TokenKind.ELIF)
                if bb:
                    branches.append(bb)

            if cur.peek().kind == TokenKind.ELSE:
                bb = parse_branch(TokenKind.ELSE)
                if bb:
                    branches.append(bb)

        # Allow trailing newlines inside the rule block.
        consume_newlines()
        expect(TokenKind.DEDENT, "SD101", "Expected end of indented rule body")

        if name is None:
            name = "<missing>"
        if context is None:
            context = "<missing>"

        if not branches:
            add("SD201", "Rule must contain at least one branch", rule_tok)

        return ast.Rule(
            name=name,
            context=context,
            branches=tuple(branches),
            span=ast.SourceSpan(line=rule_tok.line, column=rule_tok.column),
        )

    rules: list[ast.Rule] = []

    consume_newlines()
    while cur.peek().kind != TokenKind.EOF:
        t = cur.peek()
        if t.kind == TokenKind.RULE:
            rule = parse_rule_block()
            if rule is not None:
                rules.append(rule)
            consume_newlines()
            continue

        add("SD200", "Expected 'rule' at top level", t)
        skip_to_line_end()
        consume_newlines()

    return ast.SourceFile(rules=tuple(rules), path=file), sorted(diags)
