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


def test_plan_schema_and_basic_declare_golden(tmp_path: Path):
    # Produce decisions JSONL via run (intent profile).
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
    decisions_path = _write(tmp_path, "decisions.jsonl", run_res.output)

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path)])
    assert plan_res.exit_code == 0
    golden = Path("tests/golden/plan_basic.json").read_text(encoding="utf-8")
    assert plan_res.output == golden

    # Basic schema sanity.
    arr = json.loads(plan_res.output)
    assert isinstance(arr, list) and len(arr) >= 1
    for p in arr:
        assert p["schema"] == "sigmadsl.plan"
        assert p["schema_version"] == "2.0-b"
        assert p["plan_id"].startswith("P")
        assert p["source_decision_id"].startswith("D")
        assert p["status"] in ("planned", "blocked", "skipped")


def test_plan_conflict_ignores_overridden_intents_golden(tmp_path: Path):
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

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path)])
    assert plan_res.exit_code == 0
    golden = Path("tests/golden/plan_conflict.json").read_text(encoding="utf-8")
    assert plan_res.output == golden

    arr = json.loads(plan_res.output)
    assert isinstance(arr, list)
    assert len(arr) == 1, "expected only the effective intent to become a plan"
    assert arr[0]["plan_action"] == "cancel"


def test_blocked_intents_produce_blocked_plans(tmp_path: Path):
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

    plan_res = runner.invoke(app, ["plan", "--input", str(decisions_path)])
    assert plan_res.exit_code == 0

    arr = json.loads(plan_res.output)
    assert isinstance(arr, list) and len(arr) >= 1
    assert all(p["status"] == "blocked" for p in arr)
    assert all(isinstance(p.get("blocked_by"), list) and p["blocked_by"] for p in arr)


def test_plan_rejects_malformed_jsonl(tmp_path: Path):
    p = _write(tmp_path, "bad.jsonl", "{not json}\n")
    res = runner.invoke(app, ["plan", "--input", str(p)])
    assert res.exit_code != 0
    assert "SD610" in res.output


def test_replay_equivalence_for_plan(tmp_path: Path):
    log_path = tmp_path / "intent_runlog.json"

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
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0
    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0

    decisions_run = _write(tmp_path, "run.jsonl", run_res.output)
    decisions_replay = _write(tmp_path, "replay.jsonl", replay_res.output)

    plan_run = runner.invoke(app, ["plan", "--input", str(decisions_run)])
    plan_replay = runner.invoke(app, ["plan", "--input", str(decisions_replay)])
    assert plan_run.exit_code == 0
    assert plan_replay.exit_code == 0
    assert plan_run.output == plan_replay.output

