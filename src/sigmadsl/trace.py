from __future__ import annotations

from dataclasses import dataclass

from .runtime_models import dec_str


def _json_value(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v
    # Avoid JSON float nondeterminism: normalize Decimals to stable strings.
    try:
        # Decimal is intentionally not imported here to keep this module small;
        # detect by attribute presence.
        if v.__class__.__name__ == "Decimal":
            return dec_str(v)  # type: ignore[arg-type]
    except Exception:
        pass
    return str(v)


@dataclass(frozen=True)
class ActionTrace:
    verb: str
    args: dict[str, object]
    decision_id: str

    def to_dict(self) -> dict:
        return {
            "verb": self.verb,
            "args": {k: _json_value(v) for k, v in self.args.items()},
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class BranchPredicateTrace:
    branch_kind: str  # when | elif | else
    expr: str | None
    result: bool | None  # else is always None; unknown/error reserved for later

    def to_dict(self) -> dict:
        return {
            "branch_kind": self.branch_kind,
            "expr": self.expr,
            "result": self.result,
        }


@dataclass(frozen=True)
class RuleTrace:
    rule_name: str
    context: str
    evaluated_branches: tuple[BranchPredicateTrace, ...]
    selected_branch: str | None  # when | elif | else | None
    fired: bool
    decisions_emitted: tuple[str, ...]
    actions: tuple[ActionTrace, ...] = ()

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "context": self.context,
            "evaluated_branches": [b.to_dict() for b in self.evaluated_branches],
            "selected_branch": self.selected_branch,
            "fired": self.fired,
            "decisions_emitted": list(self.decisions_emitted),
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass(frozen=True)
class EventTrace:
    symbol: str
    index: int
    timestamp: str
    rules: tuple[RuleTrace, ...]

    def to_dict(self) -> dict:
        return {
            "event": {"symbol": self.symbol, "index": self.index, "timestamp": self.timestamp},
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass(frozen=True)
class RunTrace:
    engine_version: str
    events: tuple[EventTrace, ...]

    def to_dict(self) -> dict:
        return {
            "engine_version": self.engine_version,
            "events": [e.to_dict() for e in self.events],
        }
