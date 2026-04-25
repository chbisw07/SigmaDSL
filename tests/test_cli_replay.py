import json
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_run_log_out_and_replay_equivalence(tmp_path: Path):
    log_path = tmp_path / "runlog.json"

    run_res = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0
    assert replay_res.output == run_res.output

    replay_res2 = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res2.exit_code == 0
    assert replay_res2.output == replay_res.output

    # Basic sanity check of log schema/content.
    d = json.loads(log_path.read_text(encoding="utf-8"))
    assert d["schema"] == "sigmadsl.runlog"
    assert d["schema_version"] == "1.0-b"
    assert d["profile"] == "signal"
    assert d["input"]["csv"]["path"] == "tests/fixtures/run/bars_basic.csv"
    assert len(d["input"]["events"]) == 3
    assert d["rules"]["files"][0]["path"] == "tests/fixtures/eval/rules_basic.sr"
    assert d["indicators"]["registry_version"] == "0.5-a"
    assert "ema@1" in d["indicators"]["pinned"]
    # rules_basic has no indicator calls.
    assert d["indicators"]["referenced"] == []


def test_cli_run_log_out_records_referenced_indicators(tmp_path: Path):
    log_path = tmp_path / "runlog.json"

    run_res = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_indicators.sr",
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    d = json.loads(log_path.read_text(encoding="utf-8"))
    assert d["schema_version"] == "1.0-b"
    assert d["indicators"]["referenced"] == ["atr@1", "ema@1", "rsi@1", "vwap@1"]


def test_cli_replay_rejects_wrong_schema(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text('{"schema":"nope","schema_version":"0.4-a"}\n', encoding="utf-8")
    res = runner.invoke(app, ["replay", "--log", str(p)])
    assert res.exit_code != 0
    assert "SD541" in res.output


def test_cli_run_option_log_out_and_replay_equivalence(tmp_path: Path):
    log_path = tmp_path / "opt_runlog.json"

    run_res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "option",
            "--input",
            "tests/fixtures/options/options_basic.csv",
            "--rules",
            "tests/fixtures/options/option_signals.sr",
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0
    assert replay_res.output == run_res.output

    # Basic sanity check of option log schema/content.
    d = json.loads(log_path.read_text(encoding="utf-8"))
    assert d["schema"] == "sigmadsl.runlog"
    assert d["schema_version"] == "1.0-b"
    assert d["profile"] == "signal"
    assert d["input"]["kind"] == "option"
    assert d["input"]["csv"]["path"] == "tests/fixtures/options/options_basic.csv"
    assert len(d["input"]["events"]) == 3
    assert d["input"]["events"][0]["snapshot"]["contract_id"].startswith("OPT:")


def test_cli_run_option_select_log_out_and_replay_equivalence(tmp_path: Path):
    log_path = tmp_path / "opt_sel_runlog.json"

    run_res = runner.invoke(
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
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0
    assert replay_res.output == run_res.output
