from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .plan_ir import PlanIR


def generate_plans(decisions: list[dict], *, source: Path | None = None) -> tuple[list[PlanIR] | None, list[Diagnostic]]:
    """
    Sprint v2.0-B: generate deterministic broker-agnostic plans from decision JSONL dicts.

    Rules (sprint contract):
    - only uses intent decisions with `is_effective=true`
    - overridden intents are ignored (no plan record)
    - blocked intents produce plans with status="blocked" and blocked_by populated
    - ordering is deterministic
    """

    diags: list[Diagnostic] = []
    intents: list[tuple[int, dict]] = []

    for idx, d in enumerate(decisions):
        def _err(msg: str) -> None:
            diags.append(
                diag(
                    code="SD710",
                    severity=Severity.error,
                    message=msg,
                    file=source,
                    line=idx + 1,
                    column=1,
                )
            )

        if not isinstance(d, dict):
            _err("Decision stream must contain JSON objects")
            continue

        if d.get("kind") != "intent":
            continue

        eff = d.get("is_effective", True)
        if eff is not True:
            continue

        intents.append((idx + 1, d))

    if diags:
        return None, sorted(diags)

    def _decision_num(did: str) -> int:
        try:
            digits: list[str] = []
            for ch in str(did):
                if ch.isdigit():
                    digits.append(ch)
                elif digits:
                    break
            return int("".join(digits)) if digits else 10**18
        except Exception:
            return 10**18

    # Deterministic ordering independent of JSONL file ordering (but consistent with it).
    def _intent_sort_key(item: tuple[int, dict]) -> tuple[int, str, int, str, str]:
        _line, d = item
        event_index = d.get("event_index")
        if not isinstance(event_index, int):
            event_index = 10**18
        symbol = str(d.get("symbol", ""))
        did = str(d.get("id", ""))
        plan_action = str(d.get("intent_action", ""))
        rule_name = str(d.get("rule_name", ""))
        return (event_index, symbol, _decision_num(did), plan_action, rule_name)

    ordered = sorted(intents, key=_intent_sort_key)

    plans: list[PlanIR] = []
    for i, (line_no, d) in enumerate(ordered, start=1):
        def _err_here(msg: str) -> None:
            diags.append(
                diag(
                    code="SD711",
                    severity=Severity.error,
                    message=msg,
                    file=source,
                    line=line_no,
                    column=1,
                )
            )

        did = d.get("id")
        rule_name = d.get("rule_name")
        event_index = d.get("event_index")
        symbol = d.get("symbol")
        timestamp = d.get("timestamp")
        intent_kind = d.get("intent_kind")
        plan_action = d.get("intent_action")
        quantity = d.get("quantity")
        percent = d.get("percent")
        enforcement = d.get("enforcement")

        if not isinstance(did, str):
            _err_here("Intent decision missing/invalid 'id'")
            continue
        if not isinstance(rule_name, str):
            _err_here("Intent decision missing/invalid 'rule_name'")
            continue
        if not isinstance(event_index, int):
            _err_here("Intent decision missing/invalid 'event_index'")
            continue
        if not isinstance(symbol, str):
            _err_here("Intent decision missing/invalid 'symbol'")
            continue
        if not isinstance(timestamp, str):
            _err_here("Intent decision missing/invalid 'timestamp'")
            continue
        if plan_action not in ("declare", "cancel"):
            _err_here("Intent decision missing/invalid 'intent_action'")
            continue
        if intent_kind is not None and not isinstance(intent_kind, str):
            _err_here("Intent decision has invalid 'intent_kind'")
            continue

        qty_dec: Decimal | None = None
        pct_dec: Decimal | None = None
        if quantity is not None:
            if not isinstance(quantity, str):
                _err_here("Intent decision has invalid 'quantity' (expected decimal string or null)")
                continue
            qty_dec = Decimal(quantity)
        if percent is not None:
            if not isinstance(percent, str):
                _err_here("Intent decision has invalid 'percent' (expected decimal string or null)")
                continue
            pct_dec = Decimal(percent)

        status = "planned"
        blocked_by: tuple[str, ...] | None = None
        if isinstance(enforcement, dict) and enforcement.get("status") == "blocked":
            status = "blocked"
            bb = enforcement.get("blocked_by")
            if isinstance(bb, list) and all(isinstance(x, str) for x in bb):
                blocked_by = tuple(bb)
            else:
                blocked_by = tuple()

        plans.append(
            PlanIR(
                plan_id=f"P{i:04d}",
                source_decision_id=did,
                rule_name=rule_name,
                event_index=event_index,
                symbol=symbol,
                timestamp=timestamp,
                intent_kind=intent_kind,
                plan_action=plan_action,
                size_quantity=qty_dec,
                size_percent=pct_dec,
                status=status,
                blocked_by=blocked_by,
            )
        )

    if diags:
        return None, sorted(diags)

    return plans, []


@dataclass(frozen=True)
class PlanOutput:
    plans: tuple[PlanIR, ...]

    def to_json(self) -> str:
        return json.dumps([p.to_dict() for p in self.plans], sort_keys=True, indent=2) + "\n"
