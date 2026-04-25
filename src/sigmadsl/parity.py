from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .decision_profiles import DecisionProfile, parse_profile
from .diagnostics import Diagnostic, diag
from .evaluator import CompiledRule, EvalResult, evaluate_chain, evaluate_option, evaluate_underlying
from .planner import PlanOutput, generate_plans
from .runner import (
    decision_jsonl_lines,
    load_compiled_rules,
    replay_from_log,
    run_chain_from_csv_with_log,
    run_option_from_csv_with_log,
    run_underlying_from_csv_with_log,
)


@dataclass(frozen=True)
class ParityCase:
    name: str
    context: str  # "underlying" | "option" | "chain"
    profile: DecisionProfile
    input_csv: Path
    rules: Path
    risk_rules: Path | None = None
    contract_id: str | None = None  # option only


@dataclass(frozen=True)
class ParityOutputs:
    decisions_jsonl: str
    plan_json: str
    plan_with_risk_json: str


@dataclass(frozen=True)
class ParityResult:
    backtest: ParityOutputs
    replay: ParityOutputs
    simulated_live: ParityOutputs


def load_parity_case(path: Path) -> tuple[ParityCase | None, list[Diagnostic]]:
    """
    Load a parity-case JSON fixture. This is intentionally strict and deterministic.
    """

    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return None, [
            diag(
                code="SD800",
                severity=Severity.error,
                message=f"Invalid parity case JSON: {e}",
                file=path,
            )
        ]

    def _err(msg: str) -> list[Diagnostic]:
        return [diag(code="SD800", severity=Severity.error, message=msg, file=path)]

    if not isinstance(d, dict):
        return None, _err("Parity case must be a JSON object")

    name = d.get("name")
    context = d.get("context")
    profile_s = d.get("profile")
    input_csv = d.get("input_csv")
    rules = d.get("rules")
    risk_rules = d.get("risk_rules")
    contract_id = d.get("contract_id")

    if not isinstance(name, str):
        return None, _err("Parity case missing/invalid 'name'")
    if not isinstance(context, str) or context.strip().lower() not in ("underlying", "option", "chain"):
        return None, _err("Parity case missing/invalid 'context'")
    if not isinstance(profile_s, str):
        return None, _err("Parity case missing/invalid 'profile'")
    profile = parse_profile(profile_s)
    if profile is None:
        return None, _err("Parity case has invalid 'profile' (expected signal|intent|risk)")
    if not isinstance(input_csv, str):
        return None, _err("Parity case missing/invalid 'input_csv'")
    if not isinstance(rules, str):
        return None, _err("Parity case missing/invalid 'rules'")
    if risk_rules is not None and not isinstance(risk_rules, str):
        return None, _err("Parity case invalid 'risk_rules'")
    if contract_id is not None and not isinstance(contract_id, str):
        return None, _err("Parity case invalid 'contract_id'")

    base = path.parent
    inp = (base / input_csv).resolve()
    r = (base / rules).resolve()
    rr = (base / risk_rules).resolve() if risk_rules is not None else None

    return (
        ParityCase(
            name=name,
            context=context.strip().lower(),
            profile=profile,
            input_csv=inp,
            rules=r,
            risk_rules=rr,
            contract_id=contract_id,
        ),
        [],
    )


def run_parity_case(case: ParityCase, *, tmp_dir: Path, with_risk_plans: bool = True) -> tuple[ParityResult | None, list[Diagnostic]]:
    """
    Sprint v2.0-D: deterministic parity harness.

    Compares:
    - backtest (`sigmadsl run` behavior) via runner functions
    - replay (`sigmadsl replay`) via runlog
    - simulated-live: deterministic event-by-event evaluation by re-evaluating the growing prefix and emitting only new decisions

    Outputs compared (strict):
    - decisions JSONL
    - plan JSON (v2.0-B)
    - plan --with-risk JSON (v2.0-C), when `with_risk_plans=True`
    """

    log_path = tmp_dir / f"{case.name}.runlog.json"

    backtest_res, backtest_diags = _run_backtest(case, log_path=log_path)
    if backtest_diags:
        return None, backtest_diags
    assert backtest_res is not None

    replay_res, replay_diags = replay_from_log(log_path=log_path)
    if replay_diags:
        return None, replay_diags
    assert replay_res is not None

    sim_jsonl, sim_diags = _run_simulated_live_decisions(case)
    if sim_diags:
        return None, sim_diags

    backtest_jsonl = "".join(decision_jsonl_lines(backtest_res))
    replay_jsonl = "".join(decision_jsonl_lines(replay_res))

    # Plan generation (broker-agnostic, derived from decisions JSONL).
    backtest_plans, backtest_plans_risk, plan_diags = _plans_from_jsonl(
        backtest_jsonl, with_risk=with_risk_plans, source=case.input_csv
    )
    if plan_diags:
        return None, plan_diags
    replay_plans, replay_plans_risk, plan_diags = _plans_from_jsonl(
        replay_jsonl, with_risk=with_risk_plans, source=case.input_csv
    )
    if plan_diags:
        return None, plan_diags
    sim_plans, sim_plans_risk, plan_diags = _plans_from_jsonl(
        sim_jsonl, with_risk=with_risk_plans, source=case.input_csv
    )
    if plan_diags:
        return None, plan_diags

    out = ParityResult(
        backtest=ParityOutputs(
            decisions_jsonl=backtest_jsonl,
            plan_json=backtest_plans,
            plan_with_risk_json=backtest_plans_risk,
        ),
        replay=ParityOutputs(
            decisions_jsonl=replay_jsonl,
            plan_json=replay_plans,
            plan_with_risk_json=replay_plans_risk,
        ),
        simulated_live=ParityOutputs(
            decisions_jsonl=sim_jsonl,
            plan_json=sim_plans,
            plan_with_risk_json=sim_plans_risk,
        ),
    )
    return out, []


def _run_backtest(case: ParityCase, *, log_path: Path) -> tuple[EvalResult | None, list[Diagnostic]]:
    if case.context == "underlying":
        return run_underlying_from_csv_with_log(
            rules_path=case.rules,
            input_csv=case.input_csv,
            profile=case.profile,
            risk_rules_path=case.risk_rules,
            log_out=log_path,
        )
    if case.context == "option":
        return run_option_from_csv_with_log(
            rules_path=case.rules,
            input_csv=case.input_csv,
            profile=case.profile,
            risk_rules_path=case.risk_rules,
            contract_id=case.contract_id,
            select=None,
            right=None,
            expiry=None,
            target_delta=None,
            log_out=log_path,
        )
    return run_chain_from_csv_with_log(
        rules_path=case.rules,
        input_csv=case.input_csv,
        profile=case.profile,
        log_out=log_path,
    )


def _plans_from_jsonl(text: str, *, with_risk: bool, source: Path) -> tuple[str, str, list[Diagnostic]]:
    # Parse decision JSONL into dicts.
    decisions: list[dict] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            return "", "", [
                diag(
                    code="SD610",
                    severity=Severity.error,
                    message="Invalid JSONL: line is not valid JSON",
                    file=source,
                    line=i,
                    column=1,
                )
            ]
        if not isinstance(obj, dict):
            return "", "", [
                diag(
                    code="SD610",
                    severity=Severity.error,
                    message="Invalid JSONL: each line must be a JSON object",
                    file=source,
                    line=i,
                    column=1,
                )
            ]
        decisions.append(obj)

    plans, diags = generate_plans(decisions, with_risk=False, source=source)
    if diags:
        return "", "", diags
    assert plans is not None
    base = PlanOutput(plans=tuple(plans)).to_json()

    if not with_risk:
        return base, "", []

    plans_r, diags = generate_plans(decisions, with_risk=True, source=source)
    if diags:
        return "", "", diags
    assert plans_r is not None
    risk_json = PlanOutput(plans=tuple(plans_r)).to_json()
    return base, risk_json, []


def _run_simulated_live_decisions(case: ParityCase) -> tuple[str | None, list[Diagnostic]]:
    """
    Deterministic simulated-live mode:
    - consumes the same fixture input event-by-event
    - at each step, re-evaluates the growing prefix using the same evaluator
    - emits only newly-produced decisions (stable by decision id)

    This is intentionally a parity harness (not a production live engine).
    """

    ctx = case.context
    prof = case.profile

    compiled, rule_diags = load_compiled_rules(case.rules, profile=prof)
    if rule_diags:
        return None, rule_diags

    risk_compiled: list[CompiledRule] | None = None
    if case.risk_rules is not None:
        rc, risk_diags = load_compiled_rules(case.risk_rules, profile=DecisionProfile.risk)
        if risk_diags:
            return None, risk_diags
        risk_compiled = rc

    from .csv_input import load_chain_events_csv, load_option_events_csv, load_underlying_events_csv

    if ctx == "underlying":
        events, diags = load_underlying_events_csv(case.input_csv)
        if diags:
            return None, diags
        return _sim_live_eval_underlying(compiled, events, profile=prof, risk_rules=risk_compiled), []

    if ctx == "option":
        events, diags = load_option_events_csv(case.input_csv, contract_id=case.contract_id)
        if diags:
            return None, diags
        compiled_opt = [c for c in compiled if c.rule.context == "option"]
        rr_opt = [c for c in (risk_compiled or []) if c.rule.context == "option"] if risk_compiled is not None else None
        return _sim_live_eval_option(compiled_opt, events, profile=prof, risk_rules=rr_opt), []

    events, diags = load_chain_events_csv(case.input_csv)
    if diags:
        return None, diags
    compiled_chain = [c for c in compiled if c.rule.context == "chain"]
    return _sim_live_eval_chain(compiled_chain, events, profile=prof), []


def _sim_live_collect_jsonl(eval_results: list[EvalResult]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for res in eval_results:
        for d in res.decisions:
            if d.id in seen:
                continue
            seen.add(d.id)
            lines.append(json.dumps(d.to_dict(), sort_keys=True) + "\n")
    return "".join(lines)


def _sim_live_eval_underlying(
    rules: list[CompiledRule], events: list, *, profile: DecisionProfile, risk_rules: list[CompiledRule] | None
) -> str:
    results: list[EvalResult] = []
    for i in range(len(events)):
        res = evaluate_underlying(rules, events[: i + 1], profile=profile, risk_rules=risk_rules, engine_version="v2.0-d")
        results.append(res)
    return _sim_live_collect_jsonl(results)


def _sim_live_eval_option(
    rules: list[CompiledRule], events: list, *, profile: DecisionProfile, risk_rules: list[CompiledRule] | None
) -> str:
    results: list[EvalResult] = []
    for i in range(len(events)):
        res = evaluate_option(rules, events[: i + 1], profile=profile, risk_rules=risk_rules, engine_version="v2.0-d")
        results.append(res)
    return _sim_live_collect_jsonl(results)


def _sim_live_eval_chain(rules: list[CompiledRule], events: list, *, profile: DecisionProfile) -> str:
    results: list[EvalResult] = []
    for i in range(len(events)):
        res = evaluate_chain(rules, events[: i + 1], profile=profile, engine_version="v2.0-d")
        results.append(res)
    return _sim_live_collect_jsonl(results)
