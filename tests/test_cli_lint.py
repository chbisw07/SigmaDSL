from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def _golden(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_cli_lint_ok_on_examples_pack():
    result = runner.invoke(app, ["lint", "examples/equity_min_rules/"])
    assert result.exit_code == 0
    assert result.output == "OK\n"


def test_cli_lint_assignment_in_condition_golden():
    src = "tests/fixtures/lint/invalid/assignment_in_condition.sr"
    result = runner.invoke(app, ["lint", src])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/lint_assignment_in_condition.txt")


def test_cli_lint_forbidden_function_call_golden():
    src = "tests/fixtures/lint/invalid/forbidden_function_call.sr"
    result = runner.invoke(app, ["lint", src])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/lint_forbidden_function_call.txt")


def test_cli_lint_profile_violation_verb_golden():
    src = "tests/fixtures/lint/invalid/profile_violation_verb.sr"
    result = runner.invoke(app, ["lint", src])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/lint_profile_violation_verb.txt")


def test_cli_lint_loop_stmt_golden():
    src = "tests/fixtures/lint/invalid/loop_stmt.sr"
    result = runner.invoke(app, ["lint", src])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/lint_loop_stmt.txt")


def test_cli_lint_function_def_stmt_golden():
    src = "tests/fixtures/lint/invalid/function_def_stmt.sr"
    result = runner.invoke(app, ["lint", src])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/lint_function_def_stmt.txt")

