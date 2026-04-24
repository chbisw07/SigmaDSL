from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_explain_d0003_golden():
    result = runner.invoke(
        app,
        [
            "explain",
            "--decision-id",
            "D0003",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/explain_d0003.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_explain_rule_not_fired_golden():
    result = runner.invoke(
        app,
        [
            "explain",
            "--rule",
            "EQ: Breakout",
            "--event-index",
            "0",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/explain_rule_breakout_event0.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_explain_blocked_decision_golden():
    result = runner.invoke(
        app,
        [
            "explain",
            "--decision-id",
            "D0001",
            "--input",
            "examples/risk_rules/data/bars_basic.csv",
            "--rules",
            "examples/risk_rules/packs/signal_always",
            "--risk-rules",
            "examples/risk_rules/packs/risk_block_close",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/explain_blocked_d0001.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_explain_option_d0001_golden():
    result = runner.invoke(
        app,
        [
            "explain",
            "--context",
            "option",
            "--decision-id",
            "D0001",
            "--input",
            "tests/fixtures/options/options_basic.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/explain_option_d0001.txt").read_text(encoding="utf-8")
    assert result.output == golden
