from __future__ import annotations

from enum import Enum


class DecisionProfile(str, Enum):
    signal = "signal"
    intent = "intent"
    risk = "risk"


DECISION_SCHEMA = "sigmadsl.decision"
DECISION_SCHEMA_VERSION = "1.0-b"


def parse_profile(s: str) -> DecisionProfile | None:
    v = (s or "").strip().lower()
    try:
        return DecisionProfile(v)
    except Exception:
        return None


def allowed_verbs(profile: DecisionProfile) -> set[str]:
    if profile == DecisionProfile.signal:
        return {"emit_signal", "annotate"}
    if profile == DecisionProfile.intent:
        return {"declare_intent", "cancel_intent", "annotate"}
    if profile == DecisionProfile.risk:
        return {"constrain_max_position", "block", "annotate"}
    return set()


def decision_kind_for_verb(verb: str) -> str:
    """
    Stable decision kind classification used for output schema.

    Kinds (v1.0-A):
    - signal: signal decisions
    - intent: intent decisions
    - constraint: risk/constraint decisions
    - annotation: non-effect notes
    """

    v = (verb or "").strip()
    if v == "emit_signal":
        return "signal"
    if v == "annotate":
        return "annotation"
    if v in ("declare_intent", "cancel_intent"):
        return "intent"
    if v in ("constrain_max_position", "block"):
        return "constraint"
    return "unknown"
