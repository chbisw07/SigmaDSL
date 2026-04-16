from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_diff_equal_golden(tmp_path: Path):
    log1 = tmp_path / "a.json"
    log2 = tmp_path / "b.json"

    r1 = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
            "--log-out",
            str(log1),
        ],
    )
    assert r1.exit_code == 0

    r2 = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
            "--log-out",
            str(log2),
        ],
    )
    assert r2.exit_code == 0

    diff_res = runner.invoke(app, ["diff", str(log1), str(log2)])
    assert diff_res.exit_code == 0
    golden = Path("tests/golden/diff_equal.txt").read_text(encoding="utf-8")
    assert diff_res.output == golden


def test_cli_diff_first_divergence_golden(tmp_path: Path):
    log1 = tmp_path / "a.json"
    log2 = tmp_path / "b.json"

    r1 = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
            "--log-out",
            str(log1),
        ],
    )
    assert r1.exit_code == 0

    r2 = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic_variant.sr",
            "--log-out",
            str(log2),
        ],
    )
    assert r2.exit_code == 0

    diff_res = runner.invoke(app, ["diff", str(log1), str(log2)])
    assert diff_res.exit_code == 1
    golden = Path("tests/golden/diff_first_divergence.txt").read_text(encoding="utf-8")
    assert diff_res.output == golden

