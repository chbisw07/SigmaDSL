from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_validate_directory_reports_sorted_diagnostics_golden():
    path = Path("tests/fixtures/invalid_dir")
    golden = Path("tests/golden/validate_invalid_dir.txt").read_text(encoding="utf-8")
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code != 0
    assert result.output == golden

