import json
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app
from sigmadsl.parser import parse_source


runner = CliRunner()

EXAMPLES_DIR = Path("examples/equity_indicator_rules")


def test_indicator_examples_pack_files_parse_cleanly():
    sr_files = sorted(p for p in EXAMPLES_DIR.rglob("*.sr") if p.is_file())
    assert len(sr_files) >= 8

    for path in sr_files:
        ast, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
        assert diags == [], f"{path} unexpectedly produced diagnostics: {diags}"
        assert ast is not None
        assert len(ast.rules) >= 1


def test_cli_validate_and_lint_indicator_examples_pack_directory_ok():
    v = runner.invoke(app, ["validate", str(EXAMPLES_DIR)])
    assert v.exit_code == 0
    assert v.output == "OK\n"

    l = runner.invoke(app, ["lint", str(EXAMPLES_DIR)])
    assert l.exit_code == 0
    assert l.output == "OK\n"


def test_cli_run_indicator_example_packs_match_expected_outputs():
    cases = [
        (
            EXAMPLES_DIR / "data/bars_trend.csv",
            EXAMPLES_DIR / "packs/trend_following",
            EXAMPLES_DIR / "expected/run_trend_following.jsonl",
        ),
        (
            EXAMPLES_DIR / "data/bars_reversion.csv",
            EXAMPLES_DIR / "packs/mean_reversion",
            EXAMPLES_DIR / "expected/run_mean_reversion.jsonl",
        ),
        (
            EXAMPLES_DIR / "data/bars_volatility.csv",
            EXAMPLES_DIR / "packs/volatility_filters",
            EXAMPLES_DIR / "expected/run_volatility_filters.jsonl",
        ),
    ]

    for input_csv, rules_dir, expected_path in cases:
        expected = expected_path.read_text(encoding="utf-8")
        res = runner.invoke(
            app,
            [
                "run",
                "--input",
                str(input_csv),
                "--rules",
                str(rules_dir),
            ],
        )
        assert res.exit_code == 0
        assert res.output == expected


def test_replay_equivalence_for_indicator_example_pack(tmp_path: Path):
    log_path = tmp_path / "trend_runlog.json"
    input_csv = EXAMPLES_DIR / "data/bars_trend.csv"
    rules_dir = EXAMPLES_DIR / "packs/trend_following"

    run_res = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(input_csv),
            "--rules",
            str(rules_dir),
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0
    assert replay_res.output == run_res.output

    d = json.loads(log_path.read_text(encoding="utf-8"))
    assert d["schema_version"] == "1.0-b"
    assert d["profile"] == "signal"
    assert sorted(d["indicators"]["referenced"]) == ["ema@1", "rsi@1", "vwap@1"]
