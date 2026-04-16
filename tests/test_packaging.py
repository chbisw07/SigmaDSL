import hashlib
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_cli_pack_and_validate_pack_ok(tmp_path: Path):
    out = tmp_path / "pack_ok.zip"
    res = runner.invoke(
        app,
        [
            "pack",
            "tests/fixtures/imports/pack_ok/main.sr",
            "--out",
            str(out),
            "--name",
            "pack_ok",
            "--version",
            "0.1.0",
        ],
    )
    assert res.exit_code == 0
    assert out.exists()

    v = runner.invoke(app, ["validate", "--pack", str(out)])
    assert v.exit_code == 0
    assert v.output == "OK\n"


def test_pack_is_deterministic_over_repeated_creation(tmp_path: Path):
    out1 = tmp_path / "a.zip"
    out2 = tmp_path / "b.zip"

    r1 = runner.invoke(
        app,
        ["pack", "tests/fixtures/imports/pack_ok/main.sr", "--out", str(out1), "--name", "x", "--version", "0.1.0"],
    )
    r2 = runner.invoke(
        app,
        ["pack", "tests/fixtures/imports/pack_ok/main.sr", "--out", str(out2), "--name", "x", "--version", "0.1.0"],
    )
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert _sha256_file(out1) == _sha256_file(out2)


def test_validate_pack_detects_tampering(tmp_path: Path):
    out = tmp_path / "pack_ok.zip"
    runner.invoke(
        app,
        ["pack", "tests/fixtures/imports/pack_ok/main.sr", "--out", str(out), "--name", "x", "--version", "0.1.0"],
    )
    assert out.exists()

    # Tamper by rewriting the zip while keeping manifest unchanged.
    import zipfile

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.endswith("rules/pack_ok/main.sr") or info.filename.endswith("rules/main.sr"):
                data = data + b"\n# tampered\n"
            zout.writestr(info, data)

    res = runner.invoke(app, ["validate", "--pack", str(tampered)])
    assert res.exit_code != 0
    assert "SD634" in res.output  # hash mismatch


def test_pack_fails_on_missing_import(tmp_path: Path):
    out = tmp_path / "missing.zip"
    res = runner.invoke(
        app,
        ["pack", "tests/fixtures/imports/pack_missing/main.sr", "--out", str(out), "--name", "x", "--version", "0.1.0"],
    )
    assert res.exit_code != 0
    assert "SD601" in res.output


def test_pack_fails_on_import_cycle(tmp_path: Path):
    out = tmp_path / "cycle.zip"
    res = runner.invoke(
        app,
        [
            "pack",
            "tests/fixtures/imports/pack_cycle_direct/a.sr",
            "--out",
            str(out),
            "--name",
            "x",
            "--version",
            "0.1.0",
        ],
    )
    assert res.exit_code != 0
    assert "SD603" in res.output


def test_validate_pack_typechecks_embedded_sources(tmp_path: Path):
    out = tmp_path / "bad_types.zip"
    res = runner.invoke(
        app,
        [
            "pack",
            "tests/fixtures/typecheck/invalid/bad_comparison_types.sr",
            "--out",
            str(out),
            "--name",
            "bad_types",
            "--version",
            "0.1.0",
        ],
    )
    assert res.exit_code == 0
    v = runner.invoke(app, ["validate", "--pack", str(out)])
    assert v.exit_code != 0
    assert "SD300" in v.output
