from __future__ import annotations

import json

from .evaluator import EvalResult
from .runtime_models import dec_str


def explain_decision(result: EvalResult, decision_id: str) -> str | None:
    """
    Sprint 0.4-B: richer explain output for a decision.

    Deterministic, human-readable, and stable for goldens.
    """

    decision = next((d for d in result.decisions if d.id == decision_id), None)
    if decision is None:
        return None

    emitting_rule, emitting_event = _find_emitting_rule_trace(result, decision_id)

    lines: list[str] = []
    lines.append("Explain (decision)\n")
    lines.append(f"- id: {decision.id}\n")
    lines.append(f"- kind: {decision.kind}\n")
    lines.append(f"- rule: {decision.rule_name}\n")
    lines.append(f"- event: {decision.symbol} #{decision.event_index} @ {decision.timestamp}\n")
    lines.append("\n")

    if emitting_rule is None or emitting_event is None:
        lines.append("Trace: <not found>\n")
        lines.append(_json_block("Decision", decision.to_dict()))
        return "".join(lines)

    # Summarize why it fired.
    lines.append("Why it fired\n")
    lines.append(f"- selected_branch: {emitting_rule.selected_branch}\n")
    for bp in emitting_rule.evaluated_branches:
        if bp.branch_kind == "else":
            continue
        expr = bp.expr or "<missing>"
        lines.append(f"- {bp.branch_kind}: {expr} => {bp.result}\n")
    if emitting_rule.selected_branch == "else":
        lines.append("- else: selected (no prior branch matched)\n")
    if emitting_rule.actions:
        lines.append("- actions:\n")
        for a in emitting_rule.actions:
            args = ", ".join(f"{k}={_value_str(v)}" for k, v in sorted(a.args.items(), key=lambda kv: kv[0]))
            lines.append(f"  - {a.verb}({args}) -> {a.decision_id}\n")
    lines.append("\n")

    lines.append(_json_block("Decision", decision.to_dict()))
    lines.append(
        _json_block(
            "Trace",
            {
                "event": emitting_event.to_dict()["event"],
                "rule": emitting_rule.to_dict(),
            },
        )
    )
    return "".join(lines)


def explain_rule_at_event(result: EvalResult, *, rule_name: str, event_index: int) -> str | None:
    """
    Sprint 0.4-B: explain why a rule fired or did not fire at a specific event index.
    """

    if event_index < 0 or event_index >= len(result.trace.events):
        return None

    ev = result.trace.events[event_index]
    rt = next((r for r in ev.rules if r.rule_name == rule_name), None)
    if rt is None:
        return None

    lines: list[str] = []
    lines.append("Explain (rule)\n")
    lines.append(f"- rule: {rt.rule_name}\n")
    lines.append(f"- context: {rt.context}\n")
    lines.append(f"- event: {ev.symbol} #{ev.index} @ {ev.timestamp}\n")
    lines.append(f"- fired: {rt.fired}\n")
    lines.append(f"- selected_branch: {rt.selected_branch}\n")
    lines.append("\n")

    lines.append("Predicate outcomes\n")
    for bp in rt.evaluated_branches:
        if bp.branch_kind == "else":
            lines.append("- else\n")
            continue
        expr = bp.expr or "<missing>"
        lines.append(f"- {bp.branch_kind}: {expr} => {bp.result}\n")

    if not rt.fired:
        lines.append("\n")
        lines.append("Why it did not fire\n")
        if rt.selected_branch is None:
            lines.append("- no branch matched\n")
        else:
            lines.append(f"- selected_branch={rt.selected_branch!r} but no actions emitted\n")

    if rt.actions:
        lines.append("\n")
        lines.append("Actions\n")
        for a in rt.actions:
            args = ", ".join(f"{k}={_value_str(v)}" for k, v in sorted(a.args.items(), key=lambda kv: kv[0]))
            lines.append(f"- {a.verb}({args}) -> {a.decision_id}\n")

    lines.append("\n")
    lines.append(_json_block("Trace", {"event": ev.to_dict()["event"], "rule": rt.to_dict()}))
    return "".join(lines)


def _json_block(title: str, obj: object) -> str:
    return f"{title}\n{json.dumps(obj, sort_keys=True, indent=2)}\n"


def _find_emitting_rule_trace(result: EvalResult, decision_id: str):
    emitting_rule = None
    emitting_event = None
    for ev in result.trace.events:
        for rt in ev.rules:
            if decision_id in rt.decisions_emitted:
                emitting_event = ev
                emitting_rule = rt
                break
        if emitting_rule is not None:
            break
    return emitting_rule, emitting_event


def _value_str(v: object) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    try:
        if v.__class__.__name__ == "Decimal":
            return dec_str(v)  # type: ignore[arg-type]
    except Exception:
        pass
    return str(v)
