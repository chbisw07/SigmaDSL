from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_plan_with_risk_allowed_golden(tmp_path: Path):
    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/profiles/intent_ok.sr",
        ],
    )
    assert run_res.exit_code == 0
    decisions_path = _write(tmp_path, "decisions_allowed.jsonl", run_res.output)

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path), "--with-risk"])
    assert plan_res.exit_code == 0
    golden = Path("tests/golden/plan_with_risk_allowed.json").read_text(encoding="utf-8")
    assert plan_res.output == golden


def test_plan_with_risk_blocked_golden(tmp_path: Path):
    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "examples/risk_rules/data/bars_basic.csv",
            "--rules",
            "examples/risk_rules/packs/intent_declare",
            "--risk-rules",
            "examples/risk_rules/packs/risk_cap_position",
        ],
    )
    assert run_res.exit_code == 0
    decisions_path = _write(tmp_path, "decisions_blocked.jsonl", run_res.output)

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path), "--with-risk"])
    assert plan_res.exit_code == 0
    golden = Path("tests/golden/plan_with_risk_blocked.json").read_text(encoding="utf-8")
    assert plan_res.output == golden

    # Spot-check reason extraction shape.
    arr = json.loads(plan_res.output)
    assert arr[0]["risk"]["reasons"][0]["constraint_kind"] == "max_position"
    assert arr[0]["risk"]["reasons"][0]["rule_name"].startswith("RISK:")


def test_plan_with_risk_conflict_golden(tmp_path: Path):
    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "tests/fixtures/run/bars_one.csv",
            "--rules",
            "tests/fixtures/intents/intent_conflict.sr",
        ],
    )
    assert run_res.exit_code == 0
    decisions_path = _write(tmp_path, "decisions_conflict.jsonl", run_res.output)

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path), "--with-risk"])
    assert plan_res.exit_code == 0
    golden = Path("tests/golden/plan_with_risk_conflict.json").read_text(encoding="utf-8")
    assert plan_res.output == golden


def test_plan_with_risk_missing_blocker_decision_is_fail_closed_but_non_fatal(tmp_path: Path):
    # Blocked effective intent, but blocker decision id is not present in the stream.
    decisions = [
        {
            "schema": "sigmadsl.decision",
            "schema_version": "1.0-b",
            "id": "D0001",
            "kind": "intent",
            "profile": "intent",
            "verb": "declare_intent",
            "rule_name": "INTENT: demo",
            "context": "underlying",
            "symbol": "TCS",
            "event_index": 0,
            "timestamp": "2026-01-01T09:15:00",
            "trace_ref": {"event_index": 0, "rule_name": "INTENT: demo", "action_index": 0},
            "enforcement": {"status": "blocked", "blocked_by": ["D9999"]},
            "intent_action": "declare",
            "intent_kind": "TARGET_LONG",
            "quantity": "100",
            "percent": None,
            "reason": None,
            "is_effective": True,
            "overridden_by": None,
        }
    ]
    text = "\n".join(json.dumps(d, sort_keys=True) for d in decisions) + "\n"
    p = _write(tmp_path, "missing_blocker.jsonl", text)

    plan_res = runner.invoke(app, ["plan", "--input", str(p), "--with-risk"])
    assert plan_res.exit_code == 0
    arr = json.loads(plan_res.output)
    assert arr[0]["status"] == "blocked"
    assert arr[0]["risk"]["status"] == "blocked"
    assert arr[0]["risk"]["blocked_by"] == ["D9999"]
    assert arr[0]["risk"]["reasons"][0]["decision_id"] == "D9999"
    assert arr[0]["risk"]["reasons"][0]["rule_name"] == "<missing>"


def test_plan_with_risk_requires_enforcement_field_fail_closed(tmp_path: Path):
    decisions = [
        {
            "schema": "sigmadsl.decision",
            "schema_version": "1.0-b",
            "id": "D0001",
            "kind": "intent",
            "profile": "intent",
            "verb": "declare_intent",
            "rule_name": "INTENT: demo",
            "context": "underlying",
            "symbol": "TCS",
            "event_index": 0,
            "timestamp": "2026-01-01T09:15:00",
            "trace_ref": {"event_index": 0, "rule_name": "INTENT: demo", "action_index": 0},
            # enforcement missing on purpose
            "intent_action": "declare",
            "intent_kind": "TARGET_LONG",
            "quantity": "100",
            "percent": None,
            "reason": None,
            "is_effective": True,
            "overridden_by": None,
        }
    ]
    text = "\n".join(json.dumps(d, sort_keys=True) for d in decisions) + "\n"
    p = _write(tmp_path, "missing_enforcement.jsonl", text)

    res = runner.invoke(app, ["plan", "--input", str(p), "--with-risk"])
    assert res.exit_code != 0
    assert "SD712" in res.output


def test_replay_parity_for_plan_with_risk(tmp_path: Path):
    log_path = tmp_path / "risk_intent.runlog.json"
    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "examples/risk_rules/data/bars_basic.csv",
            "--rules",
            "examples/risk_rules/packs/intent_declare",
            "--risk-rules",
            "examples/risk_rules/packs/risk_cap_position",
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0
    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0

    decisions_run = _write(tmp_path, "run.jsonl", run_res.output)
    decisions_replay = _write(tmp_path, "replay.jsonl", replay_res.output)

    plan_run = runner.invoke(app, ["plan", "--input", str(decisions_run), "--with-risk"])
    plan_replay = runner.invoke(app, ["plan", "--input", str(decisions_replay), "--with-risk"])
    assert plan_run.exit_code == 0
    assert plan_replay.exit_code == 0
    assert plan_run.output == plan_replay.output

