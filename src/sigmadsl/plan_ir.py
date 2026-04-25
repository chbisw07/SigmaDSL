from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .runtime_models import dec_str


PLAN_SCHEMA = "sigmadsl.plan"
PLAN_SCHEMA_VERSION = "2.0-b"
PLAN_SCHEMA_VERSION_WITH_RISK = "2.0-c"


@dataclass(frozen=True)
class PlanRiskReason:
    decision_id: str
    rule_name: str
    constraint_kind: str
    reason: str | None

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "rule_name": self.rule_name,
            "constraint_kind": self.constraint_kind,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PlanRiskMeta:
    status: str  # "allowed" | "blocked" | "unknown"
    blocked_by: tuple[str, ...]
    reasons: tuple[PlanRiskReason, ...]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "blocked_by": list(self.blocked_by),
            "reasons": [r.to_dict() for r in self.reasons],
        }


@dataclass(frozen=True)
class PlanIR:
    plan_id: str
    source_decision_id: str
    rule_name: str
    event_index: int
    symbol: str
    timestamp: str
    intent_kind: str | None
    plan_action: str  # "declare" | "cancel"
    size_quantity: Decimal | None
    size_percent: Decimal | None
    status: str  # "planned" | "blocked" | "skipped"
    blocked_by: tuple[str, ...] | None = None
    risk: PlanRiskMeta | None = None
    schema_version: str = PLAN_SCHEMA_VERSION

    def to_dict(self) -> dict:
        d = {
            "schema": PLAN_SCHEMA,
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "source_decision_id": self.source_decision_id,
            "rule_name": self.rule_name,
            "event_index": self.event_index,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "intent_kind": self.intent_kind,
            "plan_action": self.plan_action,
            "size": {
                "quantity": dec_str(self.size_quantity) if self.size_quantity is not None else None,
                "percent": dec_str(self.size_percent) if self.size_percent is not None else None,
            },
            "status": self.status,
            "blocked_by": list(self.blocked_by) if self.blocked_by is not None else None,
        }
        if self.risk is not None:
            d["risk"] = self.risk.to_dict()
        return d
