from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_cli_profile_trend_following_pack_json_golden():
    res = runner.invoke(app, ["profile", "examples/equity_indicator_rules/packs/trend_following"])
    assert res.exit_code == 0
    golden = Path("tests/golden/profile_trend_following.json").read_text(encoding="utf-8")
    assert res.output == golden

