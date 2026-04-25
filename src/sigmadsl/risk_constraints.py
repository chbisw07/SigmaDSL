from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decisions import ConstraintDecision, Decision, IntentDecision


@dataclass(frozen=True)
class _ConstraintSummary:
    blocks: tuple[str, ...]  # constraint decision ids (block-all)
    max_position: tuple[str, Decimal] | None  # (constraint id, quantity)
    unknown: tuple[str, ...]  # unsupported constraint kinds (treated as block-all)


def applied_blocks_for_event(
    *,
    primary_decisions: list[Decision],
    constraints: list[ConstraintDecision],
    event_index: int,
) -> dict[str, tuple[str, ...]]:
    """
    v1.0-B: apply risk constraints to prior decisions in a fail-closed way.

    Current semantics (Sprint scope):
    - constraint_kind="block": blocks all non-risk decisions at the same event index
    - constraint_kind="max_position": blocks intent declare decisions whose quantity exceeds the max
    - unknown constraint kinds: treated as block-all (fail-closed)

    Returns:
    - mapping of decision_id -> blocked_by constraint decision ids (stable ordering)
    """

    summary = _summarize(constraints=constraints, event_index=event_index)
    if not summary.blocks and summary.max_position is None and not summary.unknown:
        return {}

    blocked: dict[str, set[str]] = {}

    # If any "unknown" constraints exist, treat as block-all.
    block_all_ids = set(summary.blocks) | set(summary.unknown)

    for d in primary_decisions:
        if d.event_index != event_index:
            continue
        # Do not block constraints themselves; we only apply to prior non-risk decisions.
        if d.kind in ("constraint", "annotation"):
            continue
        # v2.0-A: overridden intents are ignored by risk enforcement.
        if isinstance(d, IntentDecision) and not getattr(d, "is_effective", True):
            continue
        blockers: set[str] = set()

        if block_all_ids:
            blockers |= block_all_ids

        if summary.max_position is not None and isinstance(d, IntentDecision):
            cid, max_qty = summary.max_position
            if d.intent_action == "declare" and d.quantity is not None and d.quantity > max_qty:
                blockers.add(cid)

        if blockers:
            blocked[d.id] = blockers

    return {k: tuple(sorted(v)) for k, v in sorted(blocked.items())}


def _summarize(*, constraints: list[ConstraintDecision], event_index: int) -> _ConstraintSummary:
    blocks: list[str] = []
    unknown: list[str] = []
    max_pos: tuple[str, Decimal] | None = None

    for c in constraints:
        if c.event_index != event_index:
            continue
        if c.constraint_kind == "block":
            blocks.append(c.id)
            continue
        if c.constraint_kind == "max_position":
            if c.quantity is None:
                unknown.append(c.id)
                continue
            if max_pos is None:
                max_pos = (c.id, c.quantity)
            else:
                # Most restrictive wins (deterministic).
                if c.quantity < max_pos[1]:
                    max_pos = (c.id, c.quantity)
            continue
        unknown.append(c.id)

    return _ConstraintSummary(
        blocks=tuple(sorted(blocks)),
        max_position=max_pos,
        unknown=tuple(sorted(unknown)),
    )
