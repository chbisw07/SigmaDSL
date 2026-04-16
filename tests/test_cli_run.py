from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_run_basic_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_basic.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_percent_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_percent.csv",
            "--rules",
            "tests/fixtures/eval/rules_percent.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_percent.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_reports_csv_shape_errors_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_missing_col.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_missing_col.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_format_json_is_stable():
    result = runner.invoke(
        app,
        [
            "run",
            "--format",
            "json",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert result.exit_code == 0
    # JSON array output; keep this check conservative.
    assert result.output.startswith("[\n  {")
    assert '"id": "D0001"' in result.output

