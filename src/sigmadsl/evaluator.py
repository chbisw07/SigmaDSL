from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from . import ast
from .builtins import function_names, verb_signatures
from .decision_profiles import DecisionProfile, allowed_verbs as allowed_verbs_for_profile
from .decisions import (
    AnnotationDecision,
    ConstraintDecision,
    Decision,
    IntentDecision,
    SignalDecision,
)
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
from .runtime_models import UnderlyingEvent, dec
from .trace import ActionTrace, BranchPredicateTrace, EventTrace, RuleTrace, RunTrace
from .indicators import (
    IndicatorCache,
    IndicatorDef,
    atr as ind_atr,
    ema as ind_ema,
    indicator_registry,
    rsi as ind_rsi,
    series_from_history,
    vwap as ind_vwap,
)


class EvalError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledRule:
    file: Path | None
    index_in_file: int
    rule: ast.Rule

    def order_key(self) -> tuple[str, int, str]:
        file_s = str(self.file) if self.file is not None else ""
        return (file_s, self.index_in_file, self.rule.name)


@dataclass(frozen=True)
class EvalResult:
    decisions: tuple[Decision, ...]
    trace: RunTrace

    def to_dict(self) -> dict:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
            "trace": self.trace.to_dict(),
        }


def compile_source_file(sf: ast.SourceFile) -> list[CompiledRule]:
    return [
        CompiledRule(file=sf.path, index_in_file=i, rule=r)
        for i, r in enumerate(sf.rules)
    ]


def evaluate_underlying(
    rules: list[CompiledRule],
    events: list[UnderlyingEvent],
    *,
    profile: DecisionProfile = DecisionProfile.signal,
    engine_version: str = "v0.3-a",
) -> EvalResult:
    # Deterministic ordering: file path + source order + rule name.
    ordered_rules = sorted(rules, key=lambda r: r.order_key())

    decisions: list[Decision] = []
    event_traces: list[EventTrace] = []
    indicator_cache = IndicatorCache()
    indicators: dict[str, IndicatorDef] = indicator_registry()

    decision_counter = 0

    def next_id() -> str:
        nonlocal decision_counter
        decision_counter += 1
        return f"D{decision_counter:04d}"

    for pos, ev in enumerate(events):
        if ev.index != pos:
            raise EvalError(
                "UnderlyingEvent.index must match its position in the events list "
                f"(expected {pos}, got {ev.index})"
            )
        rule_traces: list[RuleTrace] = []
        history = events[: pos + 1]

        for compiled in ordered_rules:
            rule = compiled.rule
            if rule.context != "underlying":
                # v0.3-A supports equity underlying only.
                continue

            evaluated_branches: list[BranchPredicateTrace] = []
            selected_branch: ast.Branch | None = None
            selected_kind: str | None = None
            action_traces: list[ActionTrace] = []

            for br in rule.branches:
                if br.kind == "else":
                    evaluated_branches.append(BranchPredicateTrace(branch_kind="else", expr=None, result=None))
                    if selected_branch is None:
                        selected_branch = br
                        selected_kind = "else"
                    break

                assert br.condition is not None
                result = _eval_predicate(br.condition.node, ev, history, indicator_cache, indicators)
                evaluated_branches.append(
                    BranchPredicateTrace(branch_kind=br.kind, expr=br.condition.text, result=result)
                )
                if result and selected_branch is None:
                    selected_branch = br
                    selected_kind = br.kind
                    break

            emitted_ids: list[str] = []
            if selected_branch is not None and selected_kind is not None:
                allowed_verbs = allowed_verbs_for_profile(profile)
                for action_index, then_line in enumerate(selected_branch.actions):
                    verb = then_line.call.name
                    if verb not in allowed_verbs:
                        # Fail closed; this should already be prevented by validate/lint.
                        raise EvalError(f"Verb {verb!r} is not allowed for profile {profile.value!r}")
                    args_items = [
                        (a.name, _eval_value(a.value.node, ev, history, indicator_cache, indicators))
                        for a in then_line.call.args
                    ]
                    # Stable args order for trace readability.
                    args = {k: v for k, v in sorted(args_items, key=lambda kv: kv[0])}
                    did = next_id()
                    emitted_ids.append(did)
                    action_traces.append(ActionTrace(verb=verb, args=args, decision_id=did))

                    trace_ref = {"event_index": ev.index, "rule_name": rule.name, "action_index": action_index}

                    if verb == "emit_signal":
                        kind = args.get("kind")
                        reason = args.get("reason")
                        strength = args.get("strength")
                        if not isinstance(kind, str):
                            raise EvalError("emit_signal.kind must be a string")
                        if reason is not None and not isinstance(reason, str):
                            raise EvalError("emit_signal.reason must be a string")
                        if strength is not None and not isinstance(strength, Decimal):
                            raise EvalError("emit_signal.strength must be a number")
                        decisions.append(
                            SignalDecision(
                                id=did,
                                kind="signal",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                signal_kind=kind,
                                reason=reason,
                                strength=strength,
                            )
                        )
                    elif verb == "annotate":
                        note = args.get("note")
                        if not isinstance(note, str):
                            raise EvalError("annotate.note must be a string")
                        decisions.append(
                            AnnotationDecision(
                                id=did,
                                kind="annotation",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                note=note,
                            )
                        )
                    elif verb == "declare_intent":
                        ik = args.get("kind")
                        qty = args.get("quantity")
                        pct = args.get("percent")
                        reason = args.get("reason")
                        if not isinstance(ik, str):
                            raise EvalError("declare_intent.kind must be a string")
                        if qty is not None and not isinstance(qty, Decimal):
                            raise EvalError("declare_intent.quantity must be a number")
                        if pct is not None and not isinstance(pct, Decimal):
                            raise EvalError("declare_intent.percent must be a number")
                        if reason is not None and not isinstance(reason, str):
                            raise EvalError("declare_intent.reason must be a string")
                        decisions.append(
                            IntentDecision(
                                id=did,
                                kind="intent",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                intent_action="declare",
                                intent_kind=ik,
                                quantity=qty,
                                percent=pct,
                                reason=reason,
                            )
                        )
                    elif verb == "cancel_intent":
                        reason = args.get("reason")
                        if reason is not None and not isinstance(reason, str):
                            raise EvalError("cancel_intent.reason must be a string")
                        decisions.append(
                            IntentDecision(
                                id=did,
                                kind="intent",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                intent_action="cancel",
                                intent_kind=None,
                                quantity=None,
                                percent=None,
                                reason=reason,
                            )
                        )
                    elif verb == "constrain_max_position":
                        qty = args.get("quantity")
                        reason = args.get("reason")
                        if not isinstance(qty, Decimal):
                            raise EvalError("constrain_max_position.quantity must be a number")
                        if reason is not None and not isinstance(reason, str):
                            raise EvalError("constrain_max_position.reason must be a string")
                        decisions.append(
                            ConstraintDecision(
                                id=did,
                                kind="constraint",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                constraint_kind="max_position",
                                reason=reason,
                                quantity=qty,
                            )
                        )
                    elif verb == "block":
                        reason = args.get("reason")
                        if not isinstance(reason, str):
                            raise EvalError("block.reason must be a string")
                        decisions.append(
                            ConstraintDecision(
                                id=did,
                                kind="constraint",
                                profile=profile,
                                verb=verb,
                                rule_name=rule.name,
                                context=rule.context,
                                symbol=ev.symbol,
                                event_index=ev.index,
                                timestamp=ev.bar.timestamp,
                                trace_ref=trace_ref,
                                constraint_kind="block",
                                reason=reason,
                                quantity=None,
                            )
                        )
                    else:
                        # Type checker and lint should prevent this.
                        raise EvalError(f"Unsupported verb at runtime: {verb!r}")

            rule_traces.append(
                RuleTrace(
                    rule_name=rule.name,
                    context=rule.context,
                    evaluated_branches=tuple(evaluated_branches),
                    selected_branch=selected_kind,
                    fired=bool(emitted_ids),
                    decisions_emitted=tuple(emitted_ids),
                    actions=tuple(action_traces),
                )
            )

        event_traces.append(
            EventTrace(symbol=ev.symbol, index=ev.index, timestamp=ev.bar.timestamp, rules=tuple(rule_traces))
        )

    return EvalResult(decisions=tuple(decisions), trace=RunTrace(engine_version=engine_version, events=tuple(event_traces)))


def _runtime_env(ev: UnderlyingEvent, history: list[UnderlyingEvent]) -> dict[str, object]:
    bar = ev.bar
    env: dict[str, object] = {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "bar.open": bar.open,
        "bar.high": bar.high,
        "bar.low": bar.low,
        "bar.close": bar.close,
        "bar.volume": bar.volume,
        "bar.time": bar.timestamp,
        "data.is_fresh": ev.data_is_fresh,
        "session.is_regular": ev.session_is_regular,
    }
    if ev.underlying_return_5m is not None:
        env["underlying.return_5m"] = ev.underlying_return_5m
    return env


def _eval_predicate(
    node: ExprNode | None,
    ev: UnderlyingEvent,
    history: list[UnderlyingEvent],
    cache: IndicatorCache,
    indicators: dict[str, IndicatorDef],
) -> bool:
    val = _eval_value(node, ev, history, cache, indicators)
    if not isinstance(val, bool):
        raise EvalError("Predicate did not evaluate to Bool")
    return val


def _eval_value(
    node: ExprNode | None,
    ev: UnderlyingEvent,
    history: list[UnderlyingEvent],
    cache: IndicatorCache,
    indicators: dict[str, IndicatorDef],
) -> object:
    if node is None:
        raise EvalError("Missing expression node")

    if isinstance(node, BoolLiteral):
        return node.value
    if isinstance(node, StringLiteral):
        return node.value
    if isinstance(node, IntLiteral):
        return dec(node.raw)
    if isinstance(node, DecimalLiteral):
        return dec(node.raw)
    if isinstance(node, PercentLiteral):
        # 0.2% => 0.002 per DSL_v0.md (12.2.1 provisional)
        return dec(node.raw) / Decimal("100")

    env = _runtime_env(ev, history)

    if isinstance(node, Name):
        if node.value in function_names() or node.value in verb_signatures():
            return node.value
        if node.value not in env:
            raise EvalError(f"Unknown identifier at runtime: {node.value!r}")
        return env[node.value]

    if isinstance(node, Attribute):
        dn = dotted_name(node)
        if dn is None or dn not in env:
            raise EvalError(f"Unknown field at runtime: {dn!r}")
        return env[dn]

    if isinstance(node, UnaryOp):
        v = _eval_value(node.operand, ev, history, cache, indicators)
        if node.op == "not":
            if not isinstance(v, bool):
                raise EvalError("'not' requires Bool")
            return not v
        if node.op == "+":
            return _as_decimal(v)
        if node.op == "-":
            return -_as_decimal(v)
        raise EvalError(f"Unsupported unary op: {node.op!r}")

    if isinstance(node, BinaryOp):
        if node.op in ("and", "or"):
            left = _eval_value(node.left, ev, history, cache, indicators)
            if not isinstance(left, bool):
                raise EvalError(f"{node.op!r} left operand must be Bool")
            if node.op == "and":
                if not left:
                    return False
                right = _eval_value(node.right, ev, history, cache, indicators)
                if not isinstance(right, bool):
                    raise EvalError(f"{node.op!r} right operand must be Bool")
                return bool(right)
            else:
                if left:
                    return True
                right = _eval_value(node.right, ev, history, cache, indicators)
                if not isinstance(right, bool):
                    raise EvalError(f"{node.op!r} right operand must be Bool")
                return bool(right)

        # arithmetic
        l = _eval_value(node.left, ev, history, cache, indicators)
        r = _eval_value(node.right, ev, history, cache, indicators)
        ld = _as_decimal(l)
        rd = _as_decimal(r)
        if node.op == "+":
            return ld + rd
        if node.op == "-":
            return ld - rd
        if node.op == "*":
            return ld * rd
        if node.op == "/":
            return ld / rd
        raise EvalError(f"Unsupported binary op: {node.op!r}")

    if isinstance(node, CompareOp):
        l = _eval_value(node.left, ev, history, cache, indicators)
        r = _eval_value(node.right, ev, history, cache, indicators)
        if isinstance(l, bool) or isinstance(r, bool):
            raise EvalError("Comparison operands must be non-bool")
        ld = _as_decimal(l) if isinstance(l, Decimal) or isinstance(l, (int, str)) else l
        rd = _as_decimal(r) if isinstance(r, Decimal) or isinstance(r, (int, str)) else r
        if isinstance(ld, Decimal) and isinstance(rd, Decimal):
            return _cmp_decimal(node.op, ld, rd)
        if isinstance(ld, str) and isinstance(rd, str):
            return _cmp_str(node.op, ld, rd)
        raise EvalError("Unsupported comparison operand types")

    if isinstance(node, Call):
        return _eval_call(node, ev, history, cache, indicators)

    raise EvalError(f"Unsupported expression node: {type(node).__name__}")


def _eval_call(
    node: Call,
    ev: UnderlyingEvent,
    history: list[UnderlyingEvent],
    cache: IndicatorCache,
    indicators: dict[str, IndicatorDef],
) -> object:
    fn = dotted_name(node.func)
    if fn is None:
        raise EvalError("Call target must be a simple function name")
    if fn not in function_names():
        raise EvalError(f"Forbidden function call at runtime: {fn!r}")
    if node.kwargs:
        raise EvalError("Keyword args not supported in v0.3-A")

    if fn == "abs":
        if len(node.args) != 1:
            raise EvalError("abs() expects 1 argument")
        return abs(_as_decimal(_eval_value(node.args[0], ev, history, cache, indicators)))

    if fn in ("highest", "lowest"):
        if len(node.args) != 2:
            raise EvalError(f"{fn}() expects 2 arguments")
        series_node = node.args[0]
        series_dn: str | None = None
        if isinstance(series_node, Name):
            series_dn = series_node.value
        elif isinstance(series_node, Attribute):
            series_dn = dotted_name(series_node)
        if series_dn is None:
            raise EvalError(f"{fn}() first arg must be a series name")
        series = series_dn
        length = int(_as_decimal(_eval_value(node.args[1], ev, history, cache, indicators)))
        if length <= 0:
            raise EvalError(f"{fn}() length must be positive")
        values = [_bar_series_value(e, series) for e in history[-length:]]
        if fn == "highest":
            return max(values)
        return min(values)

    if fn in ("prior_high", "prior_low"):
        if len(node.args) != 1:
            raise EvalError(f"{fn}() expects 1 argument")
        length = int(_as_decimal(_eval_value(node.args[0], ev, history, cache, indicators)))
        if length <= 0:
            raise EvalError(f"{fn}() length must be positive")
        prev = history[:-1]
        if not prev:
            # No history; conservative: use current bar
            prev = history
        window = prev[-length:]
        highs = [e.bar.high for e in window]
        lows = [e.bar.low for e in window]
        return max(highs) if fn == "prior_high" else min(lows)

    # Indicators (v0.5-A)
    if fn in ("ema", "rsi"):
        if len(node.args) != 2:
            raise EvalError(f"{fn}() expects 2 arguments")
        series_dn = None
        if isinstance(node.args[0], Name):
            series_dn = node.args[0].value
        elif isinstance(node.args[0], Attribute):
            series_dn = dotted_name(node.args[0])
        if series_dn is None:
            raise EvalError(f"{fn}() first arg must be a series name")
        length = int(_as_decimal(_eval_value(node.args[1], ev, history, cache, indicators)))
        if length <= 0:
            raise EvalError(f"{fn}() length must be positive")

        d = indicators.get(fn)
        if d is None:
            raise EvalError(f"Unknown indicator: {fn!r}")
        ind_key = d.id.key()

        def compute():
            series = series_from_history(history, series_dn)
            return ind_ema(series, length) if fn == "ema" else ind_rsi(series, length)

        return cache.get_or_compute(indicator_key=ind_key, params=(series_dn, length), event_index=ev.index, compute=compute)

    if fn == "atr":
        if len(node.args) != 1:
            raise EvalError("atr() expects 1 argument")
        length = int(_as_decimal(_eval_value(node.args[0], ev, history, cache, indicators)))
        if length <= 0:
            raise EvalError("atr() length must be positive")
        d = indicators.get(fn)
        if d is None:
            raise EvalError("Unknown indicator: 'atr'")
        ind_key = d.id.key()

        def compute():
            high = series_from_history(history, "high")
            low = series_from_history(history, "low")
            close = series_from_history(history, "close")
            return ind_atr(high, low, close, length)

        return cache.get_or_compute(indicator_key=ind_key, params=(length,), event_index=ev.index, compute=compute)

    if fn == "vwap":
        if len(node.args) not in (0, 1):
            raise EvalError("vwap() expects 0 or 1 arguments")
        length = None
        if len(node.args) == 1:
            length = int(_as_decimal(_eval_value(node.args[0], ev, history, cache, indicators)))
            if length <= 0:
                raise EvalError("vwap() length must be positive")
        d = indicators.get(fn)
        if d is None:
            raise EvalError("Unknown indicator: 'vwap'")
        ind_key = d.id.key()

        def compute():
            close = series_from_history(history, "close")
            vol = series_from_history(history, "volume")
            return ind_vwap(close, vol, length)

        return cache.get_or_compute(indicator_key=ind_key, params=(length,), event_index=ev.index, compute=compute)

    raise EvalError(f"Unhandled function at runtime: {fn!r}")


def _bar_series_value(ev: UnderlyingEvent, series: str) -> Decimal:
    # accept both plain and dotted forms
    if series.startswith("bar."):
        series = series.split(".", 1)[1]
    if series == "open":
        return ev.bar.open
    if series == "high":
        return ev.bar.high
    if series == "low":
        return ev.bar.low
    if series == "close":
        return ev.bar.close
    if series == "volume":
        return ev.bar.volume
    raise EvalError(f"Unknown series name: {series!r}")


def _as_decimal(v: object) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, str):
        return Decimal(v)
    raise EvalError("Expected numeric value")


def _cmp_decimal(op: str, l: Decimal, r: Decimal) -> bool:
    if op == "==":
        return l == r
    if op == "!=":
        return l != r
    if op == "<":
        return l < r
    if op == "<=":
        return l <= r
    if op == ">":
        return l > r
    if op == ">=":
        return l >= r
    raise EvalError(f"Unsupported comparison op: {op!r}")


def _cmp_str(op: str, l: str, r: str) -> bool:
    if op == "==":
        return l == r
    if op == "!=":
        return l != r
    raise EvalError(f"Unsupported string comparison op: {op!r}")
