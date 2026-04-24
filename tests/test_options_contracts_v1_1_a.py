from __future__ import annotations

import json
from pathlib import Path

from sigmadsl.options_contracts import OptionRight, parse_option_contract_id
from sigmadsl.options_snapshots import check_option_snapshot_usable, parse_option_snapshot_dict


def test_parse_option_contract_id_roundtrip():
    cid = "OPT:NSE:TCS:2026-01-29:100:CALL:150"
    c, diags = parse_option_contract_id(cid)
    assert diags == []
    assert c is not None
    assert c.venue == "NSE"
    assert c.underlying == "TCS"
    assert c.expiry.isoformat() == "2026-01-29"
    assert str(c.strike) == "100.00"
    assert c.right == OptionRight.call
    assert c.lot_size == 150
    assert c.canonical_id() == cid


def test_parse_option_contract_id_normalizes_strike():
    cid = "OPT:NSE:TCS:2026-01-29:100.5:PE:150"
    c, diags = parse_option_contract_id(cid)
    assert diags == []
    assert c is not None
    assert c.right == OptionRight.put
    assert c.canonical_id() == "OPT:NSE:TCS:2026-01-29:100.5:PUT:150"


def test_parse_option_contract_id_rejects_bad_expiry():
    c, diags = parse_option_contract_id("OPT:NSE:TCS:2026-99-01:100:CALL:150")
    assert c is None
    assert any(d.code == "SD703" for d in diags)


def test_parse_option_contract_id_rejects_bad_strike_scale():
    c, diags = parse_option_contract_id("OPT:NSE:TCS:2026-01-29:100.123:CALL:150")
    assert c is None
    assert any(d.code == "SD704" for d in diags)


def test_parse_option_snapshot_and_quality():
    d = {
        "timestamp": "2026-01-01T09:15:00",
        "contract_id": "OPT:NSE:TCS:2026-01-29:100:CALL:150",
        "last": "12.5",
        "iv": "0.25",
        "delta": "0.52",
        "data_is_fresh": True,
    }
    snap, diags = parse_option_snapshot_dict(d)
    assert diags == []
    assert snap is not None
    ok, issues = check_option_snapshot_usable(snap)
    assert ok and issues == ()
    # deterministic serialization for potential runlog usage later
    json.dumps(snap.to_dict(), sort_keys=True)


def test_option_snapshot_quality_flags_make_snapshot_unusable():
    snap, diags = parse_option_snapshot_dict(
        {
            "timestamp": "2026-01-01T09:15:00",
            "contract_id": "OPT:NSE:TCS:2026-01-29:100:CALL:150",
            "last": "12.5",
            "data_is_fresh": True,
            "quality_flags": ["bad_tick"],
        }
    )
    assert diags == []
    assert snap is not None
    ok, issues = check_option_snapshot_usable(snap)
    assert not ok
    assert "quality_flags_present" in issues


def test_option_snapshot_missing_quote_is_unusable():
    snap, diags = parse_option_snapshot_dict(
        {"timestamp": "2026-01-01T09:15:00", "contract_id": "OPT:NSE:TCS:2026-01-29:100:CALL:150", "data_is_fresh": True}
    )
    assert diags == []
    assert snap is not None
    ok, issues = check_option_snapshot_usable(snap)
    assert not ok
    assert "missing_quote" in issues


def test_option_context_rule_validates_via_cli():
    # v1.1-A scope: typed validation only (runner support for option snapshots arrives in v1.1-B).
    from typer.testing import CliRunner

    from sigmadsl.cli import app

    runner = CliRunner()
    res = runner.invoke(app, ["validate", "tests/fixtures/options/option_ok.sr", "--profile", "signal"])
    assert res.exit_code == 0
    assert res.output == "OK\n"
