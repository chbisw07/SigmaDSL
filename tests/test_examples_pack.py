from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app
from sigmadsl.parser import parse_source


runner = CliRunner()

EXAMPLES_DIR = Path("examples/equity_min_rules")
EXPECTED_OK = (EXAMPLES_DIR / "expected/validate_ok.txt").read_text(encoding="utf-8")


def test_examples_pack_files_parse_cleanly():
    sr_files = sorted(p for p in EXAMPLES_DIR.glob("*.sr") if p.is_file())
    assert len(sr_files) >= 10

    for path in sr_files:
        ast, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
        assert diags == [], f"{path} unexpectedly produced diagnostics: {diags}"
        assert ast is not None
        assert len(ast.rules) >= 1


def test_cli_validate_examples_pack_directory_golden_ok():
    result = runner.invoke(app, ["validate", str(EXAMPLES_DIR)])
    assert result.exit_code == 0
    assert result.output == EXPECTED_OK

