from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_validate_import_pack_ok():
    res = runner.invoke(app, ["validate", "tests/fixtures/imports/pack_ok/main.sr"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_lint_import_pack_ok():
    res = runner.invoke(app, ["lint", "tests/fixtures/imports/pack_ok/main.sr"])
    assert res.exit_code == 0
    assert res.output == "OK\n"


def test_run_import_pack_ok_jsonl_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/imports/pack_ok/main.sr",
        ],
    )
    assert res.exit_code == 0
    golden = Path("tests/golden/run_import_pack_ok.jsonl").read_text(encoding="utf-8")
    assert res.output == golden


def test_validate_missing_import_golden():
    res = runner.invoke(app, ["validate", "tests/fixtures/imports/pack_missing/main.sr"])
    assert res.exit_code != 0
    golden = Path("tests/golden/validate_import_missing_module.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_validate_import_cycle_direct_golden():
    res = runner.invoke(app, ["validate", "tests/fixtures/imports/pack_cycle_direct/a.sr"])
    assert res.exit_code != 0
    golden = Path("tests/golden/validate_import_cycle_direct.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_validate_import_cycle_indirect_golden():
    res = runner.invoke(app, ["validate", "tests/fixtures/imports/pack_cycle_indirect/a.sr"])
    assert res.exit_code != 0
    golden = Path("tests/golden/validate_import_cycle_indirect.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_validate_import_duplicate_module_name_golden():
    res = runner.invoke(app, ["validate", "tests/fixtures/imports/pack_duplicate"])
    assert res.exit_code != 0
    golden = Path("tests/golden/validate_import_duplicate_module.txt").read_text(encoding="utf-8")
    assert res.output == golden


def test_profile_import_pack_ok_json_golden():
    res = runner.invoke(app, ["profile", "tests/fixtures/imports/pack_ok/main.sr"])
    assert res.exit_code == 0
    golden = Path("tests/golden/profile_import_pack_ok.json").read_text(encoding="utf-8")
    assert res.output == golden

