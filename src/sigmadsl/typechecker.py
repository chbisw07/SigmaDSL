from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ast
from .builtins import function_names, option_env_types, underlying_env_types, verb_signatures
from .diagnostics import Diagnostic, Severity, diag
from .expr import (
    Attribute,
    BinaryOp,
    BoolLiteral,
    Call,
    CompareOp,
    DecimalLiteral,
    ExprNode,
    IntLiteral,
    Name,
    PercentLiteral,
    StringLiteral,
    UnaryOp,
    dotted_name,
)
from .types import (
    BOOL,
    DECIMAL,
    DECIMAL_LITERAL,
    INT,
    INT_LITERAL,
    PERCENT,
    PERCENT_LITERAL,
    PRICE,
    QUANTITY,
    STRING,
    UNKNOWN,
    Type,
    is_literal,
    is_numeric,
    literal_compatible_with,
    type_matches,
    widen_literal,
)


@dataclass(frozen=True)
class _Env:
    file: Path | None
    context: str
    names: dict[str, Type]


def typecheck_source_file(source_file: ast.SourceFile) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    file = source_file.path

    for rule in source_file.rules:
        if rule.context not in ("underlying", "option"):
            diags.append(
                diag(
                    code="SD303",
                    severity=Severity.error,
                    message=f"Unsupported context for v0.2 type checking: {rule.context!r} (expected 'underlying' or 'option')",
                    file=file,
                    line=rule.span.line,
                    column=rule.span.column,
                )
            )
            continue

        names = underlying_env_types() if rule.context == "underlying" else option_env_types()
        env = _Env(file=file, context=rule.context, names=names)

        for branch in rule.branches:
            if branch.condition is not None:
                t = infer_expr_type(branch.condition, env, diags)
                if t != BOOL and t != UNKNOWN:
                    diags.append(
                        diag(
                            code="SD300",
                            severity=Severity.error,
                            message=f"Type mismatch in condition: expected Bool, got {t}",
                            file=file,
                            line=branch.condition.span.line,
                            column=branch.condition.span.column,
                        )
                    )

            for then_line in branch.actions:
                typecheck_verb_call(then_line.call, env, diags)

    return sorted(diags)


def typecheck_verb_call(call: ast.VerbCall, env: _Env, diags: list[Diagnostic]) -> None:
    sigs = verb_signatures()
    sig = sigs.get(call.name)
    if sig is None:
        diags.append(
            diag(
                code="SD310",
                severity=Severity.error,
                message=f"Unknown verb: {call.name!r}",
                file=env.file,
                line=call.span.line,
                column=call.span.column,
            )
        )
        return

    args_by_name = {a.name: a for a in call.args}

    for req_name, req_type in sig.required.items():
        if req_name not in args_by_name:
            diags.append(
                diag(
                    code="SD311",
                    severity=Severity.error,
                    message=f"Missing required argument for {call.name}: {req_name} (expected {req_type})",
                    file=env.file,
                    line=call.span.line,
                    column=call.span.column,
                )
            )

    allowed = set(sig.required) | set(sig.optional)
    for arg_name, arg in args_by_name.items():
        if arg_name not in allowed:
            diags.append(
                diag(
                    code="SD312",
                    severity=Severity.error,
                    message=f"Unknown argument for {call.name}: {arg_name!r}",
                    file=env.file,
                    line=call.span.line,
                    column=call.span.column,
                )
            )
            continue

        expected = sig.required.get(arg_name) or sig.optional.get(arg_name)  # type: ignore[assignment]
        got = infer_expr_type(arg.value, env, diags)
        if expected is not None and got != UNKNOWN and not type_matches(expected, got):
            diags.append(
                diag(
                    code="SD313",
                    severity=Severity.error,
                    message=f"Type mismatch for {call.name}.{arg_name}: expected {expected}, got {got}",
                    file=env.file,
                    line=arg.value.span.line,
                    column=arg.value.span.column,
                )
            )


def infer_expr_type(expr: ast.Expr, env: _Env, diags: list[Diagnostic]) -> Type:
    node = expr.node
    if node is None:
        return UNKNOWN
    return _infer_node_type(node, env, diags)


def _infer_node_type(node: ExprNode, env: _Env, diags: list[Diagnostic]) -> Type:
    if isinstance(node, BoolLiteral):
        return BOOL
    if isinstance(node, StringLiteral):
        return STRING
    if isinstance(node, IntLiteral):
        return INT_LITERAL
    if isinstance(node, DecimalLiteral):
        return DECIMAL_LITERAL
    if isinstance(node, PercentLiteral):
        return PERCENT_LITERAL

    if isinstance(node, Name):
        t = env.names.get(node.value)
        if t is None:
            # allow function names without immediate error; error occurs at call site if unknown.
            if node.value in function_names():
                return UNKNOWN
            diags.append(
                diag(
                    code="SD301",
                    severity=Severity.error,
                    message=f"Unknown identifier: {node.value!r}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        return t

    if isinstance(node, Attribute):
        dn = dotted_name(node)
        if dn is None:
            diags.append(
                diag(
                    code="SD301",
                    severity=Severity.error,
                    message="Unsupported attribute base (expected dotted name)",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        t = env.names.get(dn)
        if t is None:
            diags.append(
                diag(
                    code="SD301",
                    severity=Severity.error,
                    message=f"Unknown field: {dn!r}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        return t

    if isinstance(node, Call):
        return _infer_call_type(node, env, diags)

    if isinstance(node, UnaryOp):
        ot = _infer_node_type(node.operand, env, diags)
        if node.op == "not":
            if ot != UNKNOWN and ot != BOOL:
                diags.append(
                    diag(
                        code="SD300",
                        severity=Severity.error,
                        message=f"Type mismatch for 'not': expected Bool, got {ot}",
                        file=env.file,
                        line=node.span.line,
                        column=node.span.column,
                    )
                )
            return BOOL
        if node.op in ("+", "-"):
            if ot != UNKNOWN and not is_numeric(ot):
                diags.append(
                    diag(
                        code="SD300",
                        severity=Severity.error,
                        message=f"Type mismatch for unary {node.op!r}: expected numeric, got {ot}",
                        file=env.file,
                        line=node.span.line,
                        column=node.span.column,
                    )
                )
            return widen_literal(ot)
        return UNKNOWN

    if isinstance(node, BinaryOp):
        return _infer_binary_type(node, env, diags)

    if isinstance(node, CompareOp):
        lt = _infer_node_type(node.left, env, diags)
        rt = _infer_node_type(node.right, env, diags)
        if lt == UNKNOWN or rt == UNKNOWN:
            return BOOL

        if lt == rt:
            return BOOL
        if is_literal(lt) and literal_compatible_with(lt, rt):
            return BOOL
        if is_literal(rt) and literal_compatible_with(rt, lt):
            return BOOL

        diags.append(
            diag(
                code="SD300",
                severity=Severity.error,
                message=f"Incompatible comparison: left is {lt}, right is {rt}",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return BOOL

    return UNKNOWN


def _infer_call_type(node: Call, env: _Env, diags: list[Diagnostic]) -> Type:
    fn = dotted_name(node.func)
    if fn is None:
        diags.append(
            diag(
                code="SD301",
                severity=Severity.error,
                message="Unsupported call target (expected function name)",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return UNKNOWN

    if fn not in function_names():
        diags.append(
            diag(
                code="SD301",
                severity=Severity.error,
                message=f"Unknown function: {fn!r}",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return UNKNOWN

    if node.kwargs:
        diags.append(
            diag(
                code="SD300",
                severity=Severity.error,
                message=f"Keyword arguments are not supported for {fn!r} in v0.2",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return UNKNOWN

    if fn == "abs":
        if len(node.args) != 1:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 1 argument, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        at = _infer_node_type(node.args[0], env, diags)
        if at != UNKNOWN and not is_numeric(at):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects a numeric argument, got {at}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        return widen_literal(at)

    if fn in ("highest", "lowest"):
        if len(node.args) != 2:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 2 arguments, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        series_t = _infer_node_type(node.args[0], env, diags)
        length_t = _infer_node_type(node.args[1], env, diags)
        if length_t != UNKNOWN and not type_matches(INT, length_t):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() length: expected Int, got {length_t}",
                    file=env.file,
                    line=node.args[1].span.line,
                    column=node.args[1].span.column,
                )
            )
        return widen_literal(series_t)

    if fn in ("prior_high", "prior_low"):
        if len(node.args) != 1:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 1 argument, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        length_t = _infer_node_type(node.args[0], env, diags)
        if length_t != UNKNOWN and not type_matches(INT, length_t):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() length: expected Int, got {length_t}",
                    file=env.file,
                    line=node.args[0].span.line,
                    column=node.args[0].span.column,
                )
            )
        return PRICE

    if fn == "ema":
        if len(node.args) != 2:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 2 arguments, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        series_t = _infer_node_type(node.args[0], env, diags)
        length_t = _infer_node_type(node.args[1], env, diags)
        if length_t != UNKNOWN and not type_matches(INT, length_t):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() length: expected Int, got {length_t}",
                    file=env.file,
                    line=node.args[1].span.line,
                    column=node.args[1].span.column,
                )
            )
        return widen_literal(series_t)

    if fn == "rsi":
        if len(node.args) != 2:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 2 arguments, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        _ = _infer_node_type(node.args[0], env, diags)
        length_t = _infer_node_type(node.args[1], env, diags)
        if length_t != UNKNOWN and not type_matches(INT, length_t):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() length: expected Int, got {length_t}",
                    file=env.file,
                    line=node.args[1].span.line,
                    column=node.args[1].span.column,
                )
            )
        return PERCENT

    if fn == "atr":
        if len(node.args) != 1:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 1 argument, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        length_t = _infer_node_type(node.args[0], env, diags)
        if length_t != UNKNOWN and not type_matches(INT, length_t):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() length: expected Int, got {length_t}",
                    file=env.file,
                    line=node.args[0].span.line,
                    column=node.args[0].span.column,
                )
            )
        return PRICE

    if fn == "vwap":
        if len(node.args) not in (0, 1):
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"{fn}() expects 0 or 1 arguments, got {len(node.args)}",
                    file=env.file,
                    line=node.span.line,
                    column=node.span.column,
                )
            )
            return UNKNOWN
        if len(node.args) == 1:
            length_t = _infer_node_type(node.args[0], env, diags)
            if length_t != UNKNOWN and not type_matches(INT, length_t):
                diags.append(
                    diag(
                        code="SD300",
                        severity=Severity.error,
                        message=f"{fn}() length: expected Int, got {length_t}",
                        file=env.file,
                        line=node.args[0].span.line,
                        column=node.args[0].span.column,
                    )
                )
        return PRICE

    return UNKNOWN


def _infer_binary_type(node: BinaryOp, env: _Env, diags: list[Diagnostic]) -> Type:
    lt = _infer_node_type(node.left, env, diags)
    rt = _infer_node_type(node.right, env, diags)
    if lt == UNKNOWN or rt == UNKNOWN:
        return UNKNOWN

    op = node.op
    if op in ("and", "or"):
        if lt != BOOL:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"Type mismatch for {op!r}: expected Bool on left, got {lt}",
                    file=env.file,
                    line=node.left.span.line,
                    column=node.left.span.column,
                )
            )
        if rt != BOOL:
            diags.append(
                diag(
                    code="SD300",
                    severity=Severity.error,
                    message=f"Type mismatch for {op!r}: expected Bool on right, got {rt}",
                    file=env.file,
                    line=node.right.span.line,
                    column=node.right.span.column,
                )
            )
        return BOOL

    # arithmetic (conservative)
    lt_w = widen_literal(lt)
    rt_w = widen_literal(rt)

    if op in ("+", "-"):
        if lt_w == rt_w and lt_w in (PRICE, DECIMAL, INT, PERCENT, QUANTITY):
            return lt_w
        diags.append(
            diag(
                code="SD302",
                severity=Severity.error,
                message=f"Operator {op!r} not supported for {lt_w} and {rt_w}",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return UNKNOWN

    if op in ("*", "/"):
        # numeric scaling rules (subset)
        if lt_w in (DECIMAL, INT) and rt_w in (DECIMAL, INT):
            return DECIMAL
        if lt_w == PRICE and rt_w in (DECIMAL, INT):
            return PRICE
        if rt_w == PRICE and lt_w in (DECIMAL, INT):
            return PRICE
        if lt_w == PERCENT and rt_w in (DECIMAL, INT):
            return PERCENT
        if rt_w == PERCENT and lt_w in (DECIMAL, INT):
            return PERCENT
        if op == "/" and lt_w == PRICE and rt_w == PRICE:
            return DECIMAL

        diags.append(
            diag(
                code="SD302",
                severity=Severity.error,
                message=f"Operator {op!r} not supported for {lt_w} and {rt_w}",
                file=env.file,
                line=node.span.line,
                column=node.span.column,
            )
        )
        return UNKNOWN

    return UNKNOWN
