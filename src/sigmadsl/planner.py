from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .plan_ir import (
    PLAN_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION_WITH_RISK,
    PlanIR,
    PlanRiskMeta,
    PlanRiskReason,
)


def generate_plans(
    decisions: list[dict], *, with_risk: bool = False, source: Path | None = None
) -> tuple[list[PlanIR] | None, list[Diagnostic]]:
    """
    Sprint v2.0-B: generate deterministic broker-agnostic plans from decision JSONL dicts.

    Rules (sprint contract):
    - only uses intent decisions with `is_effective=true`
    - overridden intents are ignored (no plan record)
    - blocked intents produce plans with status="blocked" and blocked_by populated
    - ordering is deterministic
    - if `with_risk=True`, every plan includes a `risk` section extracted deterministically
    """

    diags: list[Diagnostic] = []
    intents: list[tuple[int, dict]] = []

    # Index risk constraint decisions by id for blocker-reason extraction.
    # Only required when `with_risk=True`, but safe to compute always.
    risk_constraints_by_id: dict[str, dict] = {}
    for idx, d in enumerate(decisions):
        if not isinstance(d, dict):
            continue
        if d.get("kind") != "constraint" or d.get("profile") != "risk":
            continue
        cid = d.get("id")
        if not isinstance(cid, str):
            continue
        risk_constraints_by_id[cid] = d

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
        enforcement_status: str | None = None
        enforcement_blocked_by: tuple[str, ...] = ()

        if isinstance(enforcement, dict):
            s = enforcement.get("status")
            if isinstance(s, str):
                enforcement_status = s
            bb = enforcement.get("blocked_by")
            if isinstance(bb, list) and all(isinstance(x, str) for x in bb):
                enforcement_blocked_by = tuple(bb)

        if with_risk and enforcement_status is None:
            # Fail closed: when risk-aware planning is requested, enforcement must be present and well-formed.
            diags.append(
                diag(
                    code="SD712",
                    severity=Severity.error,
                    message="Risk-aware planning requires decision.enforcement.status to be present and valid",
                    file=source,
                    line=line_no,
                    column=1,
                )
            )
            continue

        if enforcement_status == "blocked":
            status = "blocked"
            blocked_by = tuple(sorted(enforcement_blocked_by))

        risk_meta: PlanRiskMeta | None = None
        schema_version = PLAN_SCHEMA_VERSION
        if with_risk:
            schema_version = PLAN_SCHEMA_VERSION_WITH_RISK
            if enforcement_status == "blocked":
                reasons: list[PlanRiskReason] = []
                for bid in sorted(set(enforcement_blocked_by)):
                    rd = risk_constraints_by_id.get(bid)
                    if rd is None:
                        reasons.append(
                            PlanRiskReason(
                                decision_id=bid,
                                rule_name="<missing>",
                                constraint_kind="<missing>",
                                reason=None,
                            )
                        )
                        continue
                    rule_n = rd.get("rule_name")
                    ck = rd.get("constraint_kind")
                    r = rd.get("reason")
                    reasons.append(
                        PlanRiskReason(
                            decision_id=bid,
                            rule_name=str(rule_n) if isinstance(rule_n, str) else "<missing>",
                            constraint_kind=str(ck) if isinstance(ck, str) else "<missing>",
                            reason=str(r) if isinstance(r, str) else None,
                        )
                    )
                risk_meta = PlanRiskMeta(status="blocked", blocked_by=tuple(sorted(set(enforcement_blocked_by))), reasons=tuple(reasons))
            elif enforcement_status == "allowed":
                risk_meta = PlanRiskMeta(status="allowed", blocked_by=(), reasons=())
            else:
                # Any non-standard enforcement status is treated as unknown (fail-closed semantics are enforced by not calling it allowed).
                risk_meta = PlanRiskMeta(status="unknown", blocked_by=tuple(sorted(set(enforcement_blocked_by))), reasons=())
                status = "blocked"
                if blocked_by is None:
                    blocked_by = tuple(sorted(enforcement_blocked_by)) if enforcement_blocked_by else tuple()

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
                risk=risk_meta,
                schema_version=schema_version,
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
