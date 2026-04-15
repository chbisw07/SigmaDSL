from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def _golden(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_cli_validate_type_non_bool_condition_golden():
    src = Path("tests/fixtures/typecheck/invalid/non_bool_condition.sr")
    result = runner.invoke(app, ["validate", str(src)])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/validate_type_non_bool_condition.txt")


def test_cli_validate_type_bad_verb_arg_type_golden():
    src = Path("tests/fixtures/typecheck/invalid/bad_verb_arg_type.sr")
    result = runner.invoke(app, ["validate", str(src)])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/validate_type_bad_verb_arg_type.txt")


def test_cli_validate_type_unknown_verb_golden():
    src = Path("tests/fixtures/typecheck/invalid/unknown_verb.sr")
    result = runner.invoke(app, ["validate", str(src)])
    assert result.exit_code != 0
    assert result.output == _golden("tests/golden/validate_type_unknown_verb.txt")

