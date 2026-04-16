import json

from typer.testing import CliRunner

from sigmadsl.cli import app


runner = CliRunner()


def test_signal_decisions_have_stable_v1_schema_envelope_and_legacy_fields():
    res = runner.invoke(
        app,
        [
            "run",
            "--input",
            "tests/fixtures/run/bars_basic.csv",
            "--rules",
            "tests/fixtures/eval/rules_basic.sr",
        ],
    )
    assert res.exit_code == 0

    lines = [l for l in res.output.splitlines() if l.strip()]
    assert lines, "expected at least one decision"

    for line in lines:
        d = json.loads(line)
        assert d["schema"] == "sigmadsl.decision"
        assert d["schema_version"] == "1.0-b"
        assert d["profile"] == "signal"
        assert d["id"].startswith("D")
        assert d["rule_name"]
        assert isinstance(d["event_index"], int)
        assert d["timestamp"]
        assert isinstance(d["trace_ref"], dict)
        assert set(d["trace_ref"].keys()) == {"action_index", "event_index", "rule_name"}
        assert isinstance(d["trace_ref"]["action_index"], int)
        assert d["verb"] in ("emit_signal", "annotate")

        assert d["enforcement"]["status"] in ("allowed", "blocked")
        assert isinstance(d["enforcement"]["blocked_by"], list)

        # Backward-compat: legacy top-level fields remain present.
        assert "kind" in d
        assert "symbol" in d
