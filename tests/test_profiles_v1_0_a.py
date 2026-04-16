from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_validate_accepts_intent_profile_for_intent_verbs():
    res = runner.invoke(app, ["validate", "tests/fixtures/profiles/intent_ok.sr", "--profile", "intent"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_validate_accepts_risk_profile_for_risk_verbs():
    res = runner.invoke(app, ["validate", "tests/fixtures/profiles/risk_ok.sr", "--profile", "risk"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_validate_rejects_intent_verb_in_signal_profile():
    res = runner.invoke(app, ["validate", "tests/fixtures/profiles/signal_profile_violation_intent_verb.sr"])
    assert res.exit_code != 0
    assert "SD410" in res.output


def test_cli_run_intent_profile_golden():
    res = runner.invoke(
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
    assert res.exit_code == 0
    golden = Path("tests/golden/run_intent.jsonl").read_text(encoding="utf-8")
    assert res.output == golden


def test_cli_run_risk_profile_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "risk",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/profiles/risk_ok.sr",
        ],
    )
    assert res.exit_code == 0
    golden = Path("tests/golden/run_risk.jsonl").read_text(encoding="utf-8")
    assert res.output == golden

