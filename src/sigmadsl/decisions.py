from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decision_profiles import DECISION_SCHEMA, DECISION_SCHEMA_VERSION, DecisionProfile
from .runtime_models import dec_str


@dataclass(frozen=True)
class Decision:
    id: str
    kind: str  # "signal" | "annotation" | "intent" | "constraint" (v1.0-A)
    profile: DecisionProfile  # signal | intent | risk
    verb: str
    rule_name: str
    context: str
    symbol: str
    event_index: int
    timestamp: str
    trace_ref: dict  # stable linkage to trace location

    def to_dict(self) -> dict:
        return {
            "schema": DECISION_SCHEMA,
            "schema_version": DECISION_SCHEMA_VERSION,
            "id": self.id,
            "kind": self.kind,
            "profile": self.profile.value,
            "verb": self.verb,
            "rule_name": self.rule_name,
            "context": self.context,
            "symbol": self.symbol,
            "event_index": self.event_index,
            "timestamp": self.timestamp,
            "trace_ref": self.trace_ref,
        }


@dataclass(frozen=True)
class SignalDecision(Decision):
    signal_kind: str
    reason: str | None = None
    strength: Decimal | None = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update(
            {
                "signal_kind": self.signal_kind,
                "reason": self.reason,
                "strength": dec_str(self.strength) if self.strength is not None else None,
            }
        )
        return d


@dataclass(frozen=True)
class AnnotationDecision(Decision):
    note: str

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"note": self.note})
        return d


@dataclass(frozen=True)
class IntentDecision(Decision):
    intent_action: str  # "declare" | "cancel"
    intent_kind: str | None = None
    quantity: Decimal | None = None
    percent: Decimal | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update(
            {
                "intent_action": self.intent_action,
                "intent_kind": self.intent_kind,
                "quantity": dec_str(self.quantity) if self.quantity is not None else None,
                "percent": dec_str(self.percent) if self.percent is not None else None,
                "reason": self.reason,
            }
        )
        return d


@dataclass(frozen=True)
class ConstraintDecision(Decision):
    constraint_kind: str
    reason: str | None = None
    quantity: Decimal | None = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update(
            {
                "constraint_kind": self.constraint_kind,
                "reason": self.reason,
                "quantity": dec_str(self.quantity) if self.quantity is not None else None,
            }
        )
        return d
