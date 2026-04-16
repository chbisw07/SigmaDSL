from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_runner_output_is_invariant_to_process_timezone():
    args = [
        "run",
        "--input",
        "tests/fixtures/run/bars_basic.csv",
        "--rules",
        "tests/fixtures/eval/rules_basic.sr",
    ]
    res_utc = runner.invoke(app, args, env={"TZ": "UTC"})
    res_ist = runner.invoke(app, args, env={"TZ": "Asia/Kolkata"})
    assert res_utc.exit_code == 0
    assert res_ist.exit_code == 0
    assert res_utc.output == res_ist.output


def test_timestamps_are_treated_as_opaque_strings_and_preserved():
    res = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic_tz.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
        env={"TZ": "UTC"},
    )
    assert res.exit_code == 0
    assert "2026-01-01T09:15:00+05:30" in res.output
    assert "2026-01-01T09:20:00+05:30" in res.output
