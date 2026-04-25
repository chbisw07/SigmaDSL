from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from sigmadsl.cli import app
from sigmadsl.decision_profiles import DecisionProfile
from sigmadsl.decisions import DecisionEnforcement, IntentDecision
from sigmadsl.intent_resolution import resolve_intents_for_event


runner = CliRunner()


def _mk_intent(
    *,
    did: str,
    action: str,
    kind: str | None,
    quantity: Decimal | None,
    percent: Decimal | None = None,
    rule_name: str = "R",
    symbol: str = "TCS",
    event_index: int = 0,
) -> IntentDecision:
    return IntentDecision(
        id=did,
        kind="intent",
        profile=DecisionProfile.intent,
        verb="declare_intent" if action == "declare" else "cancel_intent",
        rule_name=rule_name,
        context="underlying",
        symbol=symbol,
        event_index=event_index,
        timestamp="2026-01-01T09:15:00",
        trace_ref={"event_index": event_index, "rule_name": rule_name, "action_index": 0},
        enforcement=DecisionEnforcement(status="allowed", blocked_by=()),
        intent_action=action,
        intent_kind=kind,
        quantity=quantity,
        percent=percent,
        reason=None,
    )


def test_duplicate_intents_collapse_and_mark_overridden():
    intents = [
        _mk_intent(did="D0001", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="A"),
        # Different rule_name but same idempotency key (reason is not part of the key).
        _mk_intent(did="D0002", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="B"),
    ]
    effective = resolve_intents_for_event(intents)
    assert [d.id for d in effective] == ["D0001"]
    assert intents[0].is_effective is True and intents[0].overridden_by is None
    assert intents[1].is_effective is False and intents[1].overridden_by == "D0001"


def test_cancel_overrides_declare_conflict():
    intents = [
        _mk_intent(did="D0001", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="A"),
        _mk_intent(did="D0002", action="cancel", kind=None, quantity=None, rule_name="B"),
    ]
    effective = resolve_intents_for_event(intents)
    assert [d.id for d in effective] == ["D0002"]
    assert intents[1].is_effective is True
    assert intents[0].is_effective is False and intents[0].overridden_by == "D0002"


def test_quantity_based_resolution_picks_larger_absolute_quantity():
    intents = [
        _mk_intent(did="D0001", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="A"),
        _mk_intent(did="D0002", action="declare", kind="TARGET_LONG", quantity=Decimal("250"), rule_name="B"),
    ]
    effective = resolve_intents_for_event(intents)
    assert [d.id for d in effective] == ["D0002"]
    assert intents[1].is_effective is True
    assert intents[0].is_effective is False and intents[0].overridden_by == "D0002"


def test_deterministic_tie_breaking_earlier_rule_order_then_rule_name():
    # Synthetic ids to force a tie on "earlier rule order" (both parse to decision_num=1),
    # so rule_name lexical order becomes the deterministic tiebreak.
    intents = [
        _mk_intent(did="D0001X", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="B"),
        _mk_intent(did="D0001", action="declare", kind="TARGET_LONG", quantity=Decimal("100"), rule_name="A"),
    ]
    effective = resolve_intents_for_event(intents)
    assert [d.id for d in effective] == ["D0001"]
    assert intents[1].is_effective is True
    assert intents[0].is_effective is False and intents[0].overridden_by == "D0001"


def test_replay_equivalence_for_intent_conflict_case(tmp_path: Path):
    log_path = tmp_path / "intent_conflict_runlog.json"
    run_res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "tests/fixtures/run/bars_one.csv",
            "--rules",
            "tests/fixtures/intents/intent_conflict.sr",
            "--log-out",
            str(log_path),
        ],
    )
    assert run_res.exit_code == 0

    replay_res = runner.invoke(app, ["replay", "--log", str(log_path)])
    assert replay_res.exit_code == 0
    assert replay_res.output == run_res.output

    # Basic sanity: output includes at least one effective and one overridden intent.
    lines = [l for l in run_res.output.splitlines() if l.strip()]
    assert lines
    parsed = [json.loads(l) for l in lines]
    assert any(d.get("kind") == "intent" and d.get("is_effective") is True for d in parsed)
    assert any(d.get("kind") == "intent" and d.get("is_effective") is False for d in parsed)


def test_cli_run_intent_conflict_jsonl_golden():
    res = runner.invoke(
        app,
        [
            "run",
            "--profile",
            "intent",
            "--input",
            "tests/fixtures/run/bars_one.csv",
            "--rules",
            "tests/fixtures/intents/intent_conflict.sr",
        ],
    )
    assert res.exit_code == 0
    golden = Path("tests/golden/run_intent_conflict.jsonl").read_text(encoding="utf-8")
    assert res.output == golden

