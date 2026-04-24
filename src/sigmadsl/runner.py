from __future__ import annotations

import json
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .decision_profiles import DecisionProfile
from .evaluator import CompiledRule, EvalError, EvalResult, compile_source_file, evaluate_option, evaluate_underlying
from .indicators import INDICATOR_REGISTRY_VERSION, pinned_indicator_keys, referenced_indicator_keys
from .linting import lint_text
from .modules import load_modules_for_path, resolve_import_closure
from .parser import parse_source
from .runlog import (
    RUNLOG_SCHEMA,
    RUNLOG_SCHEMA_VERSION,
    CsvSourceMeta,
    IndicatorsMeta,
    RuleSource,
    RunLog,
    load_runlog,
    sha256_text,
    write_runlog,
)
from .runtime_models import UnderlyingEvent
from .options_runtime import OptionEvent
from .typechecker import typecheck_source_file


def load_compiled_rules(path: Path, *, profile: DecisionProfile) -> tuple[list[CompiledRule], list[Diagnostic]]:
    compiled, _, _, diags = load_compiled_rules_with_sources(path, profile=profile)
    return compiled, diags


def load_compiled_rules_with_sources(
    path: Path, *, profile: DecisionProfile
) -> tuple[list[CompiledRule], list[RuleSource], tuple[str, ...], list[Diagnostic]]:
    modules, index_diags, root = load_modules_for_path(path)
    if index_diags:
        return [], [], (), sorted(index_diags)

    entry_paths = [path] if path.is_file() else [m.path for m in modules]
    closure, import_diags = resolve_import_closure(root=root, modules=modules, entry_paths=entry_paths)
    if import_diags:
        return [], [], (), sorted(import_diags)

    rules: list[CompiledRule] = []
    sources: list[RuleSource] = []
    indicator_keys: set[str] = set()
    diags: list[Diagnostic] = []

    for m in closure:
        sources.append(RuleSource(path=str(m.path), sha256=sha256_text(m.text), text=m.text))

        diags.extend(m.parse_diags)
        if m.source_file is None or m.parse_diags:
            continue

        diags.extend(typecheck_source_file(m.source_file))
        diags.extend(lint_text(m.text, profile=profile, file=m.path))

        # Only include rules from modules with no diagnostics to keep execution safe.
        if not [d for d in diags if d.location.file == m.path]:
            rules.extend(compile_source_file(m.source_file))
            indicator_keys.update(referenced_indicator_keys(m.source_file))

    return rules, sources, tuple(sorted(indicator_keys)), sorted(diags)


def run_underlying_from_csv(
    *,
    rules_path: Path,
    input_csv: Path,
    profile: DecisionProfile = DecisionProfile.signal,
    risk_rules_path: Path | None = None,
    engine_version: str = "v0.3-b",
) -> tuple[EvalResult | None, list[Diagnostic]]:
    from .csv_input import load_underlying_events_csv

    compiled, rule_diags = load_compiled_rules(rules_path, profile=profile)
    if rule_diags:
        return None, rule_diags

    risk_compiled: list[CompiledRule] | None = None
    if risk_rules_path is not None:
        rc, risk_diags = load_compiled_rules(risk_rules_path, profile=DecisionProfile.risk)
        if risk_diags:
            return None, risk_diags
        risk_compiled = rc

    events, csv_diags = load_underlying_events_csv(input_csv)
    if csv_diags:
        return None, csv_diags

    try:
        return (
            evaluate_underlying(compiled, events, profile=profile, risk_rules=risk_compiled, engine_version=engine_version),
            [],
        )
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
    profile: DecisionProfile = DecisionProfile.signal,
    risk_rules_path: Path | None = None,
    engine_version: str = "v0.4-a",
    log_out: Path | None,
) -> tuple[EvalResult | None, list[Diagnostic]]:
    """
    Like `run_underlying_from_csv`, but optionally writes a self-contained replay log (Sprint 0.4-A).
    """

    from .csv_input import load_underlying_events_csv_with_meta

    compiled, sources, referenced_inds, rule_diags = load_compiled_rules_with_sources(rules_path, profile=profile)
    if rule_diags:
        return None, rule_diags

    risk_compiled: list[CompiledRule] | None = None
    risk_sources: list[RuleSource] = []
    if risk_rules_path is not None:
        risk_compiled, risk_sources, _, risk_diags = load_compiled_rules_with_sources(
            risk_rules_path, profile=DecisionProfile.risk
        )
        if risk_diags:
            return None, risk_diags

    events, meta, csv_diags = load_underlying_events_csv_with_meta(input_csv)
    if csv_diags:
        return None, csv_diags
    assert meta is not None

    try:
        result = evaluate_underlying(
            compiled, events, profile=profile, risk_rules=risk_compiled, engine_version=engine_version
        )
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
            profile=profile.value,
            input_kind="underlying",
            rules=tuple(sources),
            risk_rules=tuple(risk_sources) if risk_rules_path is not None else None,
            input_csv=CsvSourceMeta(
                path=str(input_csv),
                sha256=sha256_text(csv_text),
                columns=meta.columns,
                row_count=meta.row_count,
            ),
            events=tuple(events),
            indicators=IndicatorsMeta(
                registry_version=INDICATOR_REGISTRY_VERSION,
                pinned=pinned_indicator_keys(),
                referenced=referenced_inds,
            ),
        )
        log_diags = write_runlog(log_out, log)
        if log_diags:
            return None, log_diags

    return result, []


def run_option_from_csv_with_log(
    *,
    rules_path: Path,
    input_csv: Path,
    profile: DecisionProfile = DecisionProfile.signal,
    risk_rules_path: Path | None = None,
    contract_id: str | None = None,
    engine_version: str = "v1.1-b",
    log_out: Path | None,
) -> tuple[EvalResult | None, list[Diagnostic]]:
    """
    Sprint v1.1-B: Option snapshot runner (atomic contract-level context).

    Notes:
    - `contract_id` is required if the CSV contains multiple contracts (fail closed).
    - Context binding is explicit: rules must be authored with `in option:`.
    """

    from .csv_input import load_option_events_csv_with_meta

    compiled, sources, referenced_inds, rule_diags = load_compiled_rules_with_sources(rules_path, profile=profile)
    if rule_diags:
        return None, rule_diags

    # Require at least one option-context rule to avoid silent no-op runs.
    if not [c for c in compiled if c.rule.context == "option"]:
        return None, [
            diag(
                code="SD735",
                severity=Severity.error,
                message="No 'option' context rules found in rule pack (expected rules authored with: in option:)",
                file=rules_path,
            )
        ]

    risk_compiled: list[CompiledRule] | None = None
    risk_sources: list[RuleSource] = []
    if risk_rules_path is not None:
        risk_compiled, risk_sources, _, risk_diags = load_compiled_rules_with_sources(
            risk_rules_path, profile=DecisionProfile.risk
        )
        if risk_diags:
            return None, risk_diags

    events, meta, csv_diags = load_option_events_csv_with_meta(input_csv, contract_id=contract_id)
    if csv_diags:
        return None, csv_diags
    assert meta is not None

    # Filter compiled/risk rules to option context for this run.
    compiled_opt = [c for c in compiled if c.rule.context == "option"]
    risk_opt = [c for c in (risk_compiled or []) if c.rule.context == "option"] if risk_compiled is not None else None

    try:
        result = evaluate_option(compiled_opt, events, profile=profile, risk_rules=risk_opt, engine_version=engine_version)
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
            profile=profile.value,
            input_kind="option",
            rules=tuple(sources),
            risk_rules=tuple(risk_sources) if risk_rules_path is not None else None,
            input_csv=CsvSourceMeta(
                path=str(input_csv),
                sha256=sha256_text(csv_text),
                columns=meta.columns,
                row_count=meta.row_count,
            ),
            events=tuple(events),
            indicators=IndicatorsMeta(
                registry_version=INDICATOR_REGISTRY_VERSION,
                pinned=pinned_indicator_keys(),
                referenced=referenced_inds,
            ),
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
    risk_compiled: list[CompiledRule] = []
    all_diags: list[Diagnostic] = []

    profile = DecisionProfile.signal
    if getattr(log, "profile", None):
        try:
            profile = DecisionProfile(str(getattr(log, "profile")))
        except Exception:
            profile = DecisionProfile.signal

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
        all_diags.extend(lint_text(rs.text, profile=profile, file=Path(rs.path)))
        if not [d for d in all_diags if d.location.file == Path(rs.path)]:
            compiled.extend(compile_source_file(sf))

    if log.risk_rules is not None:
        for rs in log.risk_rules:
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
            all_diags.extend(lint_text(rs.text, profile=DecisionProfile.risk, file=Path(rs.path)))
            if not [d for d in all_diags if d.location.file == Path(rs.path)]:
                risk_compiled.extend(compile_source_file(sf))

    if all_diags:
        return None, sorted(all_diags)

    if log.indicators is not None:
        available = set(pinned_indicator_keys())
        missing = sorted(k for k in log.indicators.referenced if k not in available)
        if missing:
            return None, [
                diag(
                    code="SD545",
                    severity=Severity.error,
                    message=f"Replay requires unsupported indicator versions: {missing!r}",
                    file=log_path,
                )
            ]

    engine_version = engine_version_override or log.engine_version
    try:
        rr = risk_compiled if log.risk_rules is not None else None

        kind = getattr(log, "input_kind", "underlying") or "underlying"
        if kind == "underlying":
            underlying_events = [e for e in list(log.events) if isinstance(e, UnderlyingEvent)]
            if len(underlying_events) != len(list(log.events)):
                return None, [
                    diag(
                        code="SD544",
                        severity=Severity.error,
                        message="Run log input kind is 'underlying' but events contain non-underlying entries",
                        file=log_path,
                    )
                ]
            return (
                evaluate_underlying(
                    compiled, underlying_events, profile=profile, risk_rules=rr, engine_version=engine_version
                ),
                [],
            )
        if kind == "option":
            # Ensure only option-context rules are used for an option replay.
            compiled_opt = [c for c in compiled if c.rule.context == "option"]
            rr_opt = [c for c in (rr or []) if c.rule.context == "option"] if rr is not None else None
            option_events = [e for e in list(log.events) if isinstance(e, OptionEvent)]
            if len(option_events) != len(list(log.events)):
                return None, [
                    diag(
                        code="SD544",
                        severity=Severity.error,
                        message="Run log input kind is 'option' but events contain non-option entries",
                        file=log_path,
                    )
                ]
            return (
                evaluate_option(
                    compiled_opt,
                    option_events,
                    profile=profile,
                    risk_rules=rr_opt,
                    engine_version=engine_version,
                ),
                [],
            )
        return None, [
            diag(
                code="SD541",
                severity=Severity.error,
                message=f"Unsupported input kind in run log: {kind!r}",
                file=log_path,
            )
        ]
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
        lines.append(json.dumps(d.to_dict(), sort_keys=True) + "\n")
    return lines


def explain_decision_text(result: EvalResult, decision_id: str) -> str | None:
    """
    Basic explain output (v0.3-B): show decision + the rule/branch trace that emitted it.
    """
    # Kept for backward compatibility; v0.4-B prefers `sigmadsl.explain.explain_decision`.
    from .explain import explain_decision

    return explain_decision(result, decision_id)
