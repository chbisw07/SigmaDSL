from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def _read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8")


def test_cli_validate_chain_worked_examples_ok():
    res = runner.invoke(app, ["validate", "examples/option_chain_context/worked_examples"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_cli_lint_chain_worked_examples_ok():
    res = runner.invoke(app, ["lint", "examples/option_chain_context/worked_examples"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_chain_worked_example_quality_gate_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_demo.csv",
            "--rules",
            "examples/option_chain_context/worked_examples/01_chain_quality_gate.sr",
        ],
    )
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/01_chain_quality_gate.jsonl")


def test_chain_worked_example_pcr_sentiment_golden_and_deterministic():
    args = [
        "run",
        "--context",
        "chain",
        "--input",
        "examples/option_chain_context/data/chain_metrics.csv",
        "--rules",
        "examples/option_chain_context/worked_examples/02_pcr_sentiment.sr",
    ]
    res = runner.invoke(app, args)
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/02_pcr_sentiment.jsonl")

    res2 = runner.invoke(app, args)
    assert res2.exit_code == 0
    assert res2.output == res.output


def test_chain_worked_example_iv_skew_alert_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_metrics.csv",
            "--rules",
            "examples/option_chain_context/worked_examples/03_iv_skew_alert.sr",
        ],
    )
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/03_iv_skew_alert.jsonl")


def test_chain_worked_example_pcr_volume_high_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_metrics.csv",
            "--rules",
            "examples/option_chain_context/worked_examples/04_pcr_volume_high.sr",
        ],
    )
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/04_pcr_volume_high.jsonl")


def test_chain_worked_example_bearish_confirmed_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_metrics.csv",
            "--rules",
            "examples/option_chain_context/worked_examples/05_bearish_confirmed.sr",
        ],
    )
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/05_bearish_confirmed.jsonl")


def test_chain_worked_example_unknown_incomplete_chain_golden_and_replay(tmp_path: Path):
    log_path = tmp_path / "runlog.json"
    res = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_incomplete_only.csv",
            "--rules",
            "examples/option_chain_context/worked_examples/06_unknown_incomplete_chain.sr",
            "--log-out",
            str(log_path),
        ],
    )
    assert res.exit_code == 0
    assert res.output == _read("examples/option_chain_context/expected/worked_examples/06_unknown_incomplete_chain.jsonl")

    replay = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay.exit_code == 0
    assert replay.output == res.output

