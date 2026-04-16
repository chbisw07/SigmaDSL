from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_report_run_basic_golden():
    res = runner.invoke(app, ["report", "--input", "tests/golden/run_basic.jsonl"])
    assert res.exit_code == 0
    golden = Path("tests/golden/report_run_basic.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_cli_report_risk_blocked_counts_golden():
    res = runner.invoke(app, ["report", "--input", "examples/risk_rules/expected/run_signal_blocked.jsonl"])
    assert res.exit_code == 0
    golden = Path("tests/golden/report_risk_signal_blocked.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_cli_report_rejects_invalid_jsonl(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_text("{not json}\n", encoding="utf-8")

    res = runner.invoke(app, ["report", "--input", str(p)])
    assert res.exit_code == 2
    assert "SD610" in res.output
