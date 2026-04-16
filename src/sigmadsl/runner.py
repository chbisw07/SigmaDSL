from __future__ import annotations

import json
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .evaluator import CompiledRule, EvalError, EvalResult, compile_source_file, evaluate_underlying
from .linting import lint_text
from .parser import parse_source
from .paths import discover_sr_files
from .typechecker import typecheck_source_file


def load_compiled_rules(path: Path) -> tuple[list[CompiledRule], list[Diagnostic]]:
    files = discover_sr_files(path)
    if not files:
        return [], [diag(code="SD000", message="No .sr files found", file=path, severity=Severity.error)]

    rules: list[CompiledRule] = []
    diags: list[Diagnostic] = []

    for file in files:
        text = file.read_text(encoding="utf-8")
        sf, parse_diags = parse_source(text, file=file)
        diags.extend(parse_diags)
        if sf is None or parse_diags:
            continue

        diags.extend(typecheck_source_file(sf))
        diags.extend(lint_text(text, file=file))

        # Only include rules from files with no diagnostics to keep execution safe.
        # This also keeps emitted decision IDs stable (fail-fast behavior).
        if not [d for d in diags if d.location.file == file]:
            rules.extend(compile_source_file(sf))

    return rules, sorted(diags)


def run_underlying_from_csv(
    *,
    rules_path: Path,
    input_csv: Path,
    engine_version: str = "v0.3-b",
) -> tuple[EvalResult | None, list[Diagnostic]]:
    from .csv_input import load_underlying_events_csv

    compiled, rule_diags = load_compiled_rules(rules_path)
    if rule_diags:
        return None, rule_diags

    events, csv_diags = load_underlying_events_csv(input_csv)
    if csv_diags:
        return None, csv_diags

    try:
        return evaluate_underlying(compiled, events, engine_version=engine_version), []
    except EvalError as e:
        return None, [
            diag(
                code="SD530",
                severity=Severity.error,
                message=f"Runtime evaluation error: {e}",
                file=input_csv,
            )
        ]


def decision_jsonl_lines(result: EvalResult) -> list[str]:
    """
    Stable JSONL decision output for Sprint 0.3-B.

    Each line is a JSON object with sorted keys.
    """

    lines: list[str] = []
    for d in result.decisions:
        o = d.to_dict()
        # Make verb explicit in the runner output schema without changing Decision.to_dict().
        if o.get("kind") == "signal":
            o["verb"] = "emit_signal"
        elif o.get("kind") == "annotation":
            o["verb"] = "annotate"
        lines.append(json.dumps(o, sort_keys=True) + "\n")
    return lines


def explain_decision_text(result: EvalResult, decision_id: str) -> str | None:
    """
    Basic explain output (v0.3-B): show decision + the rule/branch trace that emitted it.
    """

    decision = next((d for d in result.decisions if d.id == decision_id), None)
    if decision is None:
        return None

    # Find the rule trace that emitted this decision id.
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

    lines: list[str] = []
    lines.append(f"Decision {decision_id}\n")
    lines.append(json.dumps(decision.to_dict(), sort_keys=True, indent=2) + "\n")

    if emitting_event is None or emitting_rule is None:
        lines.append("Trace: <not found>\n")
        return "".join(lines)

    lines.append("Trace\n")
    lines.append(
        json.dumps(
            {
                "event": emitting_event.to_dict()["event"],
                "rule": {
                    "rule_name": emitting_rule.rule_name,
                    "context": emitting_rule.context,
                    "selected_branch": emitting_rule.selected_branch,
                    "evaluated_branches": [b.to_dict() for b in emitting_rule.evaluated_branches],
                    "actions": [a.to_dict() for a in emitting_rule.actions],
                },
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    return "".join(lines)

