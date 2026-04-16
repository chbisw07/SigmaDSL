import json
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app
from sigmadsl.parser import parse_source


runner = CliRunner()

EXAMPLES_DIR = Path("examples/risk_rules")


def test_risk_examples_pack_files_parse_cleanly():
    sr_files = sorted(p for p in EXAMPLES_DIR.rglob("*.sr") if p.is_file())
    assert len(sr_files) >= 4

    for path in sr_files:
        ast, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
        assert diags == [], f"{path} unexpectedly produced diagnostics: {diags}"
        assert ast is not None
        assert len(ast.rules) >= 1


def test_cli_validate_and_lint_risk_examples_packs_ok():
    # Signal pack
    v = runner.invoke(app, ["validate", str(EXAMPLES_DIR / "packs/signal_always"), "--profile", "signal"])
    assert v.exit_code == 0 and v.output == "OK\n"
    l = runner.invoke(app, ["lint", str(EXAMPLES_DIR / "packs/signal_always"), "--profile", "signal"])
    assert l.exit_code == 0 and l.output == "OK\n"

    # Intent pack
    v = runner.invoke(app, ["validate", str(EXAMPLES_DIR / "packs/intent_declare"), "--profile", "intent"])
    assert v.exit_code == 0 and v.output == "OK\n"
    l = runner.invoke(app, ["lint", str(EXAMPLES_DIR / "packs/intent_declare"), "--profile", "intent"])
    assert l.exit_code == 0 and l.output == "OK\n"

    # Risk packs
    for p in ("packs/risk_block_close", "packs/risk_cap_position"):
        v = runner.invoke(app, ["validate", str(EXAMPLES_DIR / p), "--profile", "risk"])
        assert v.exit_code == 0 and v.output == "OK\n"
        l = runner.invoke(app, ["lint", str(EXAMPLES_DIR / p), "--profile", "risk"])
        assert l.exit_code == 0 and l.output == "OK\n"


def test_cli_run_risk_examples_match_expected_outputs():
    cases = [
        (
            "signal",
            EXAMPLES_DIR / "data/bars_basic.csv",
            EXAMPLES_DIR / "packs/signal_always",
            EXAMPLES_DIR / "packs/risk_block_close",
            EXAMPLES_DIR / "expected/run_signal_blocked.jsonl",
        ),
        (
            "intent",
            EXAMPLES_DIR / "data/bars_basic.csv",
            EXAMPLES_DIR / "packs/intent_declare",
            EXAMPLES_DIR / "packs/risk_cap_position",
            EXAMPLES_DIR / "expected/run_intent_capped.jsonl",
        ),
    ]

    for profile, input_csv, rules_dir, risk_dir, expected_path in cases:
        expected = expected_path.read_text(encoding="utf-8")
        res = runner.invoke(
            app,
            [
                "run",
                "--profile",
                profile,
                "--input",
                str(input_csv),
                "--rules",
                str(rules_dir),
                "--risk-rules",
                str(risk_dir),
            ],
        )
        assert res.exit_code == 0
        assert res.output == expected


def test_replay_equivalence_for_risk_example(tmp_path: Path):
    log_path = tmp_path / "risk_runlog.json"
    input_csv = EXAMPLES_DIR / "data/bars_basic.csv"
    rules_dir = EXAMPLES_DIR / "packs/signal_always"
    risk_dir = EXAMPLES_DIR / "packs/risk_block_close"

    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "signal",
            "--input",
            str(input_csv),
            "--rules",
            str(rules_dir),
            "--risk-rules",
            str(risk_dir),
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
    assert "risk" in d and len(d["risk"]["rules"]["files"]) >= 1

