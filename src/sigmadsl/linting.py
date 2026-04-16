from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ast
from .builtins import function_names, verb_signatures
from .decision_profiles import DecisionProfile
from .diagnostics import Diagnostic, Severity, diag
from .expr import BinaryOp, Call, ExprNode, dotted_name
from .lexer import Token, TokenKind, lex
from .modules import load_modules_for_path, resolve_import_closure
from .parser import parse_source
from .profile_compliance import check_profile_compliance


FORBIDDEN_LINE_STARTERS = {
    "for": ("SD401", "Loops are not allowed in SigmaDSL"),
    "while": ("SD401", "Loops are not allowed in SigmaDSL"),
    "def": ("SD402", "Function definitions are not allowed in SigmaDSL"),
    "from": ("SD405", "Imports are not allowed in SigmaDSL"),
}


def lint_paths(path: Path) -> list[Diagnostic]:
    return lint_paths_with_profile(path, profile=DecisionProfile.signal)


def lint_paths_with_profile(path: Path, *, profile: DecisionProfile) -> list[Diagnostic]:
    modules, index_diags, root = load_modules_for_path(path)
    if index_diags:
        return sorted(index_diags)

    entry_paths = [path] if path.is_file() else [m.path for m in modules]
    closure, import_diags = resolve_import_closure(root=root, modules=modules, entry_paths=entry_paths)
    if import_diags:
        return sorted(import_diags)

    all_diags: list[Diagnostic] = []
    for m in closure:
        all_diags.extend(lint_text(m.text, profile=profile, file=m.path))
    return sorted(all_diags)


def lint_text(text: str, *, profile: DecisionProfile, file: Path | None = None) -> list[Diagnostic]:
    tokens, lex_diags = lex(text, file=file)
    sf, parse_diags = parse_source(text, file=file)

    diags: list[Diagnostic] = []
    diags.extend(lex_diags)

    # Parser sometimes emits SD204 for forbidden constructs; lint owns these in v0.2-B.
    diags.extend([d for d in parse_diags if d.code != "SD204"])

    diags.extend(_lint_forbidden_line_constructs(tokens, file=file))

    if sf is not None:
        diags.extend(_lint_forbidden_expr_constructs(sf, file=file))
        diags.extend(check_profile_compliance(sf, profile=profile, file=file))

    return sorted(diags)


def _lint_forbidden_line_constructs(tokens: list[Token], *, file: Path | None) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    line_tokens: list[Token] = []
    for t in tokens:
        if t.kind == TokenKind.NEWLINE:
            diags.extend(_lint_line(line_tokens, file=file))
            line_tokens = []
            continue
        if t.kind == TokenKind.EOF:
            break
        line_tokens.append(t)

    return diags


def _lint_line(tokens: list[Token], *, file: Path | None) -> list[Diagnostic]:
    # Find first non-structural token on the line.
    i = 0
    while i < len(tokens) and tokens[i].kind in (TokenKind.INDENT, TokenKind.DEDENT):
        i += 1
    if i >= len(tokens):
        return []

    first = tokens[i]
    next_tok = tokens[i + 1] if i + 1 < len(tokens) else None

    # forbidden starters
    if first.kind == TokenKind.IDENT and (first.value or "") in FORBIDDEN_LINE_STARTERS:
        code, msg = FORBIDDEN_LINE_STARTERS[first.value or ""]
        return [diag(code=code, message=msg, file=file, line=first.line, column=first.column, severity=Severity.error)]

    # assignment statement (line-level): IDENT '=' ...
    if first.kind == TokenKind.IDENT and next_tok is not None and next_tok.kind == TokenKind.EQ:
        return [
            diag(
                code="SD400",
                message="Assignments are not allowed in SigmaDSL",
                file=file,
                line=first.line,
                column=first.column,
                severity=Severity.error,
            )
        ]

    return []


def _lint_forbidden_expr_constructs(sf: ast.SourceFile, *, file: Path | None) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    allowed_functions = function_names()

    def walk(node: ExprNode | None):
        if node is None:
            return
        if isinstance(node, BinaryOp) and node.op == "=":
            diags.append(
                diag(
                    code="SD400",
                    severity=Severity.error,
                    message="Assignments are not allowed in SigmaDSL",
                    file=file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            walk(node.left)
            walk(node.right)
            return
        if isinstance(node, Call):
            dn = dotted_name(node.func)
            if dn is None:
                diags.append(
                    diag(
                        code="SD403",
                        severity=Severity.error,
                        message="Forbidden function call target (expected a simple function name)",
                        file=file,
                        line=node.span.line,
                        column=node.span.column,
                    )
                )
            elif dn not in allowed_functions:
                diags.append(
                    diag(
                        code="SD403",
                        severity=Severity.error,
                        message=f"Forbidden function call (not whitelisted): {dn!r}",
                        file=file,
                        line=node.span.line,
                        column=node.span.column,
                    )
                )
            for a in node.args:
                walk(a)
            for _, v in node.kwargs:
                walk(v)
            return

        # Generic traversal for other node shapes without importing every class:
        for child in getattr(node, "__dict__", {}).values():
            if isinstance(child, ExprNode):
                walk(child)
            elif isinstance(child, tuple):
                for item in child:
                    if isinstance(item, ExprNode):
                        walk(item)
                    elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], ExprNode):
                        walk(item[1])

    for rule in sf.rules:
        for branch in rule.branches:
            if branch.condition is not None:
                walk(branch.condition.node)
            for then_line in branch.actions:
                for arg in then_line.call.args:
                    walk(arg.value.node)

    return diags
