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


def test_cli_run_option_select_atm_call_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "atm",
            "--right",
            "CALL",
            "--input",
            "tests/fixtures/options/options_selection.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_select_atm_call.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_otm_call_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "otm",
            "--right",
            "CALL",
            "--input",
            "tests/fixtures/options/options_selection.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_select_otm_call.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_delta_call_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "delta",
            "--right",
            "CALL",
            "--target-delta",
            "0.68",
            "--input",
            "tests/fixtures/options/options_selection.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_select_delta_call.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_atm_tie_breaks_by_earlier_expiry():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "atm",
            "--right",
            "CALL",
            "--input",
            "tests/fixtures/options/options_select_tie.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_select_tie_atm.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_expiry_filter_is_respected():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "atm",
            "--right",
            "CALL",
            "--expiry",
            "2026-02-05",
            "--input",
            "tests/fixtures/options/options_select_tie.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_option_select_expiry_filter.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_otm_requires_right():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "otm",
            "--input",
            "tests/fixtures/options/options_selection.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_select_otm_missing_right.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_atm_requires_underlying_price():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "atm",
            "--right",
            "CALL",
            "--input",
            "tests/fixtures/options/options_multi_contract.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_select_missing_underlying_price.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_delta_requires_delta():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "delta",
            "--right",
            "CALL",
            "--target-delta",
            "0.5",
            "--input",
            "tests/fixtures/options/options_select_missing_delta.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_select_missing_delta.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_option_select_fails_if_no_usable_candidates():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--select",
            "atm",
            "--right",
            "CALL",
            "--input",
            "tests/fixtures/options/options_select_bad_quality.csv",
            "--rules",
            "tests/fixtures/options/option_selected_echo.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_option_select_bad_quality.txt").read_text(encoding="utf-8")
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


def test_cli_run_chain_ok_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "tests/fixtures/chain/chain_complete.csv",
            "--rules",
            "tests/fixtures/chain/chain_ok.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_chain_ok.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_chain_duplicate_contract_is_rejected():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "tests/fixtures/chain/chain_duplicate_contract.csv",
            "--rules",
            "tests/fixtures/chain/chain_ok.sr",
        ],
    )
    assert result.exit_code != 0
    golden = Path("tests/golden/run_chain_duplicate_contract.txt").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_chain_unknown_policy_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "tests/fixtures/chain/chain_incomplete.csv",
            "--rules",
            "tests/fixtures/chain/chain_unknown_policy.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_chain_unknown_policy.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_cli_run_chain_metrics_jsonl_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "tests/fixtures/chain/chain_metrics.csv",
            "--rules",
            "tests/fixtures/chain/chain_metrics.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("tests/golden/run_chain_metrics.jsonl").read_text(encoding="utf-8")
    assert result.output == golden
