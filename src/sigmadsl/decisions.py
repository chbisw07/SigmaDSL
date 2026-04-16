from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .runtime_models import dec_str


@dataclass(frozen=True)
class Decision:
    id: str
    kind: str  # "signal" | "annotation" (v0.3-A)
    rule_name: str
    symbol: str
    event_index: int
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "rule_name": self.rule_name,
            "symbol": self.symbol,
            "event_index": self.event_index,
            "timestamp": self.timestamp,
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

