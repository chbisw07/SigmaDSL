from __future__ import annotations

from pathlib import Path

from sigmadsl.parity import load_parity_case, run_parity_case


CASES_DIR = Path("tests/fixtures/parity")


def _load(name: str):
    case, diags = load_parity_case(CASES_DIR / name)
    assert diags == []
    assert case is not None
    return case


def test_parity_basic_signal_decisions_match_all_modes(tmp_path: Path):
    case = _load("case_basic_signal.json")
    res, diags = run_parity_case(case, tmp_dir=tmp_path)
    assert diags == []
    assert res is not None

    assert res.backtest.decisions_jsonl == res.replay.decisions_jsonl
    assert res.backtest.decisions_jsonl == res.simulated_live.decisions_jsonl

    # High-signal golden: protect the base deterministic decision stream.
    golden = Path("tests/golden/parity_basic_decisions.jsonl").read_text(encoding="utf-8")
    assert res.backtest.decisions_jsonl == golden


def test_parity_intent_conflict_plans_match_all_modes(tmp_path: Path):
    case = _load("case_intent_conflict.json")
    res, diags = run_parity_case(case, tmp_dir=tmp_path)
    assert diags == []
    assert res is not None

    assert res.backtest.decisions_jsonl == res.replay.decisions_jsonl
    assert res.backtest.decisions_jsonl == res.simulated_live.decisions_jsonl

    assert res.backtest.plan_json == res.replay.plan_json
    assert res.backtest.plan_json == res.simulated_live.plan_json

    assert res.backtest.plan_with_risk_json == res.replay.plan_with_risk_json
    assert res.backtest.plan_with_risk_json == res.simulated_live.plan_with_risk_json

    golden = Path("tests/golden/parity_intent_plan.json").read_text(encoding="utf-8")
    assert res.backtest.plan_json == golden


def test_parity_intent_risk_blocked_plan_with_risk_matches_all_modes(tmp_path: Path):
    case = _load("case_intent_risk_blocked.json")
    res, diags = run_parity_case(case, tmp_dir=tmp_path)
    assert diags == []
    assert res is not None

    assert res.backtest.decisions_jsonl == res.replay.decisions_jsonl
    assert res.backtest.decisions_jsonl == res.simulated_live.decisions_jsonl

    assert res.backtest.plan_with_risk_json == res.replay.plan_with_risk_json
    assert res.backtest.plan_with_risk_json == res.simulated_live.plan_with_risk_json

    golden = Path("tests/golden/parity_with_risk_plan.json").read_text(encoding="utf-8")
    assert res.backtest.plan_with_risk_json == golden


def test_parity_option_context_decisions_match_all_modes(tmp_path: Path):
    case = _load("case_option_basic.json")
    res, diags = run_parity_case(case, tmp_dir=tmp_path)
    assert diags == []
    assert res is not None
    assert res.backtest.decisions_jsonl == res.replay.decisions_jsonl
    assert res.backtest.decisions_jsonl == res.simulated_live.decisions_jsonl


def test_parity_chain_context_decisions_match_all_modes(tmp_path: Path):
    case = _load("case_chain_metrics.json")
    res, diags = run_parity_case(case, tmp_dir=tmp_path)
    assert diags == []
    assert res is not None
    assert res.backtest.decisions_jsonl == res.replay.decisions_jsonl
    assert res.backtest.decisions_jsonl == res.simulated_live.decisions_jsonl

