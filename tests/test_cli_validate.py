from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_validate_ok():
    path = Path("tests/fixtures/valid/basic_rule.sr")
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code == 0
    assert result.stdout == "OK\n"


def test_cli_validate_reports_diagnostics_and_exits_nonzero():
    path = Path("tests/fixtures/invalid/missing_colon_rule.sr")
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code != 0
    assert "SD200" in result.output
    assert str(path) in result.output


def test_cli_validate_output_is_deterministic_golden_missing_colon_rule():
    path = Path("tests/fixtures/invalid/missing_colon_rule.sr")
    golden = Path("tests/golden/validate_missing_colon_rule.txt").read_text(encoding="utf-8")
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code != 0
    assert result.output == golden


def test_cli_validate_output_is_deterministic_golden_forbidden_assignment():
    path = Path("tests/fixtures/invalid/forbidden_assignment.sr")
    golden = Path("tests/golden/validate_forbidden_assignment.txt").read_text(encoding="utf-8")
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code != 0
    assert result.output == golden
