from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .decisions import IntentDecision


def resolve_intents_for_event(intent_list: list[IntentDecision]) -> list[IntentDecision]:
    """
    Sprint v2.0-A: deterministic intent resolution for a single event.

    Pipeline:
      RAW INTENTS -> IDEMPOTENCY -> CONFLICT RESOLUTION -> EFFECTIVE INTENTS

    Idempotency key (as required by sprint spec):
      (symbol, intent_kind, intent_action, quantity, percent)

    Side effects:
    - Mutates `intent_list` by replacing elements with updated IntentDecision objects
      containing:
        - is_effective: bool
        - overridden_by: decision id or None

    Returns:
    - Only effective intents (stable order by decision id).
    """

    if not intent_list:
        return []

    # Collect intent ids and keep a stable original order.
    ids_in_order = [d.id for d in intent_list]

    # overridden_by[id] = winner_id
    overridden_by: dict[str, str] = {}

    def decision_num(d: IntentDecision) -> int:
        # Decision ids are generated as D0001, D0002, ...; keep a conservative fallback.
        # This is used as the "earlier rule order wins" tie-breaker.
        try:
            # Extract first digit run to allow deterministic tie-break tests with synthetic ids.
            s = d.id
            digits: list[str] = []
            for ch in s:
                if ch.isdigit():
                    digits.append(ch)
                elif digits:
                    break
            return int("".join(digits)) if digits else 10**18
        except Exception:
            return 10**18

    def abs_qty(d: IntentDecision) -> Decimal:
        if d.quantity is None:
            return Decimal(0)
        try:
            return abs(d.quantity)
        except Exception:
            return Decimal(0)

    def winner_sort_key(d: IntentDecision) -> tuple[int, Decimal, int, str]:
        # Lower key wins.
        # 1) cancel overrides declare
        # 2) larger absolute quantity wins
        # 3) earlier rule order wins (approximated by earlier decision id)
        # 4) rule_name lexical order tie-break
        action_rank = 0
        if d.intent_action == "cancel":
            action_rank = 2
        elif d.intent_action == "declare":
            action_rank = 1
        return (-action_rank, -abs_qty(d), decision_num(d), d.rule_name)

    # 1) Idempotency collapse: identical idempotency key -> keep one, override the rest.
    groups: dict[tuple[object, ...], list[IntentDecision]] = {}
    for d in intent_list:
        key = (d.symbol, d.intent_kind, d.intent_action, d.quantity, d.percent)
        groups.setdefault(key, []).append(d)

    dedup_winners: dict[str, IntentDecision] = {}
    for _key, items in groups.items():
        if len(items) == 1:
            dedup_winners[items[0].id] = items[0]
            continue
        keeper = sorted(items, key=winner_sort_key)[0]
        dedup_winners[keeper.id] = keeper
        for other in items:
            if other.id != keeper.id:
                overridden_by[other.id] = keeper.id

    candidates = list(dedup_winners.values())

    # 2) Conflict resolution:
    # - cancel overrides declare (per symbol)
    # - within declares for the same (symbol, intent_kind), pick one winner
    cancel_winner_by_symbol: dict[str, IntentDecision] = {}
    cancels_by_symbol: dict[str, list[IntentDecision]] = {}
    declares_by_symbol_kind: dict[tuple[str, str | None], list[IntentDecision]] = {}

    for d in candidates:
        if d.intent_action == "cancel":
            cancels_by_symbol.setdefault(d.symbol, []).append(d)
        else:
            declares_by_symbol_kind.setdefault((d.symbol, d.intent_kind), []).append(d)

    for sym, items in cancels_by_symbol.items():
        w = sorted(items, key=winner_sort_key)[0]
        cancel_winner_by_symbol[sym] = w
        for other in items:
            if other.id != w.id:
                overridden_by[other.id] = w.id

    for (sym, kind), items in declares_by_symbol_kind.items():
        cancel_winner = cancel_winner_by_symbol.get(sym)
        if cancel_winner is not None:
            for d in items:
                overridden_by[d.id] = cancel_winner.id
            continue

        if len(items) == 1:
            continue
        w = sorted(items, key=winner_sort_key)[0]
        for other in items:
            if other.id != w.id:
                overridden_by[other.id] = w.id

    # 3) Normalize overridden_by to the ultimate effective winner for clarity/stability.
    def ultimate_winner(did: str) -> str:
        seen: set[str] = set()
        cur = did
        while cur in overridden_by:
            nxt = overridden_by[cur]
            if nxt == cur or nxt in seen:
                # Defensive: break cycles deterministically.
                break
            seen.add(cur)
            cur = nxt
        return cur

    normalized_overridden_by: dict[str, str] = {}
    for did in overridden_by:
        normalized_overridden_by[did] = ultimate_winner(did)

    # Effective intents are those not overridden by any other intent after normalization.
    effective_ids: set[str] = set(ids_in_order)
    effective_ids -= set(normalized_overridden_by.keys())

    updated_by_id: dict[str, IntentDecision] = {}
    for d in intent_list:
        if d.id in normalized_overridden_by:
            updated_by_id[d.id] = replace(
                d, is_effective=False, overridden_by=normalized_overridden_by[d.id]
            )
        else:
            updated_by_id[d.id] = replace(d, is_effective=True, overridden_by=None)

    # Mutate the passed list in-place by replacing elements.
    for i, did in enumerate(ids_in_order):
        intent_list[i] = updated_by_id[did]

    effective = [updated_by_id[did] for did in ids_in_order if did in effective_ids]
    # Stable return ordering.
    effective = sorted(effective, key=decision_num)
    return effective

