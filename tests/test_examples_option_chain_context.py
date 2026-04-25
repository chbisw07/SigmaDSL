from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_examples_option_chain_context_run_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_demo.csv",
            "--rules",
            "examples/option_chain_context/chain_quality.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("examples/option_chain_context/expected/run_chain_demo.jsonl").read_text(encoding="utf-8")
    assert result.output == golden


def test_examples_option_chain_context_metrics_run_golden():
    result = runner.invoke(
        app,
        [
            "run",
            "--context",
            "chain",
            "--input",
            "examples/option_chain_context/data/chain_metrics.csv",
            "--rules",
            "examples/option_chain_context/chain_metrics.sr",
        ],
    )
    assert result.exit_code == 0
    golden = Path("examples/option_chain_context/expected/run_chain_metrics.jsonl").read_text(encoding="utf-8")
    assert result.output == golden
