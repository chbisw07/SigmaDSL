from __future__ import annotations

import json
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .evaluator import CompiledRule, EvalError, EvalResult, compile_source_file, evaluate_underlying
from .linting import lint_text
from .parser import parse_source
from .paths import discover_sr_files
from .runlog import (
    RUNLOG_SCHEMA,
    RUNLOG_SCHEMA_VERSION,
    CsvSourceMeta,
    RuleSource,
    RunLog,
    load_runlog,
    sha256_text,
    write_runlog,
)
from .typechecker import typecheck_source_file


def load_compiled_rules(path: Path) -> tuple[list[CompiledRule], list[Diagnostic]]:
    compiled, _, diags = load_compiled_rules_with_sources(path)
    return compiled, diags


def load_compiled_rules_with_sources(path: Path) -> tuple[list[CompiledRule], list[RuleSource], list[Diagnostic]]:
    files = discover_sr_files(path)
    if not files:
        return [], [], [diag(code="SD000", message="No .sr files found", file=path, severity=Severity.error)]

    rules: list[CompiledRule] = []
    sources: list[RuleSource] = []
    diags: list[Diagnostic] = []

    for file in files:
        text = file.read_text(encoding="utf-8")
        sources.append(RuleSource(path=str(file), sha256=sha256_text(text), text=text))

        sf, parse_diags = parse_source(text, file=file)
        diags.extend(parse_diags)
        if sf is None or parse_diags:
            continue

        diags.extend(typecheck_source_file(sf))
        diags.extend(lint_text(text, file=file))

        # Only include rules from files with no diagnostics to keep execution safe.
        if not [d for d in diags if d.location.file == file]:
            rules.extend(compile_source_file(sf))

    return rules, sources, sorted(diags)


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


def run_underlying_from_csv_with_log(
    *,
    rules_path: Path,
    input_csv: Path,
    engine_version: str = "v0.4-a",
    log_out: Path | None,
) -> tuple[EvalResult | None, list[Diagnostic]]:
    """
    Like `run_underlying_from_csv`, but optionally writes a self-contained replay log (Sprint 0.4-A).
    """

    from .csv_input import load_underlying_events_csv_with_meta

    compiled, sources, rule_diags = load_compiled_rules_with_sources(rules_path)
    if rule_diags:
        return None, rule_diags

    events, meta, csv_diags = load_underlying_events_csv_with_meta(input_csv)
    if csv_diags:
        return None, csv_diags
    assert meta is not None

    try:
        result = evaluate_underlying(compiled, events, engine_version=engine_version)
    except EvalError as e:
        return None, [
            diag(
                code="SD530",
                severity=Severity.error,
                message=f"Runtime evaluation error: {e}",
                file=input_csv,
            )
        ]

    if log_out is not None:
        csv_text = input_csv.read_text(encoding="utf-8")
        log = RunLog(
            schema=RUNLOG_SCHEMA,
            schema_version=RUNLOG_SCHEMA_VERSION,
            engine_version=engine_version,
            rules=tuple(sources),
            input_csv=CsvSourceMeta(
                path=str(input_csv),
                sha256=sha256_text(csv_text),
                columns=meta.columns,
                row_count=meta.row_count,
            ),
            events=tuple(events),
        )
        log_diags = write_runlog(log_out, log)
        if log_diags:
            return None, log_diags

    return result, []


def replay_from_log(*, log_path: Path, engine_version_override: str | None = None) -> tuple[EvalResult | None, list[Diagnostic]]:
    """
    Sprint 0.4-A: Load a run log and re-evaluate deterministically from embedded snapshots.
    """

    log, diags = load_runlog(log_path)
    if diags:
        return None, diags
    assert log is not None

    compiled: list[CompiledRule] = []
    all_diags: list[Diagnostic] = []

    for rs in log.rules:
        if sha256_text(rs.text) != rs.sha256:
            all_diags.append(
                diag(
                    code="SD543",
                    severity=Severity.error,
                    message=f"Rule snapshot sha256 mismatch for {rs.path!r}",
                    file=log_path,
                )
            )
            continue

        sf, parse_diags = parse_source(rs.text, file=Path(rs.path))
        all_diags.extend(parse_diags)
        if sf is None or parse_diags:
            continue

        all_diags.extend(typecheck_source_file(sf))
        all_diags.extend(lint_text(rs.text, file=Path(rs.path)))
        if not [d for d in all_diags if d.location.file == Path(rs.path)]:
            compiled.extend(compile_source_file(sf))

    if all_diags:
        return None, sorted(all_diags)

    engine_version = engine_version_override or log.engine_version
    try:
        return evaluate_underlying(compiled, list(log.events), engine_version=engine_version), []
    except EvalError as e:
        return None, [
            diag(
                code="SD530",
                severity=Severity.error,
                message=f"Runtime evaluation error during replay: {e}",
                file=log_path,
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
