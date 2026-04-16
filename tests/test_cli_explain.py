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

