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


def test_cli_run_indicators_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_indicators.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_indicators.jsonl").read_text(encoding="utf-8")
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


def test_cli_run_option_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--input",
            "tests/fixtures/options/options_basic.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_signals.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_requires_contract_id_for_multi_contract_input():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--input",
            "tests/fixtures/options/options_multi_contract.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_multi_contract.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_contract_id_selects_one_contract_deterministically():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--contract-id",
            "OPT:NSE:INFY:2026-01-29:1500:PUT:300",
            "--input",
            "tests/fixtures/options/options_multi_contract.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_multi_contract_selected.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_stale_snapshot_is_rejected():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--input",
            "tests/fixtures/options/options_stale.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_stale.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_quality_flags_are_rejected():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--input",
            "tests/fixtures/options/options_quality_flags.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_quality_flags.txt").read_text(encoding="utf-8")
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
