from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .chain_snapshots import ChainSnapshot
from .options_contracts import OptionRight


@dataclass(frozen=True)
class _Unknown:
    def __repr__(self) -> str:  # pragma: no cover
        return "UNKNOWN"


UNKNOWN = _Unknown()


def is_unknown(v: object) -> bool:
    return v is UNKNOWN


# v1.2-B: deterministic rounding policy for derived chain metrics.
PCR_QUANTUM = Decimal("0.0001")  # 4 dp ratio
SKEW_QUANTUM = Decimal("0.000001")  # 6 dp (matches OptionSnapshot IV quantization)


def _quantize(v: Decimal, q: Decimal) -> Decimal:
    return v.quantize(q, rounding=ROUND_HALF_UP)


def _ensure_metrics_allowed(snapshot: ChainSnapshot) -> bool:
    # Fail closed: derived metrics require a complete, fresh, unflagged atomic snapshot.
    return bool(snapshot.is_complete) and bool(snapshot.data_is_fresh) and not bool(snapshot.quality_flags) and not bool(snapshot.has_unknowns)


def _sum_ints(values: list[int]) -> int:
    s = 0
    for v in values:
        s += int(v)
    return s


def pcr_oi(snapshot: ChainSnapshot) -> Decimal | _Unknown:
    """
    Put/Call Open Interest ratio.

    v1.2-B policy:
    - requires snapshot quality_ok
    - requires open_interest on all contracts in the snapshot
    - requires at least one PUT and one CALL
    - denominator (CALL OI sum) must be > 0
    - result is quantized to PCR_QUANTUM
    """

    if not _ensure_metrics_allowed(snapshot):
        return UNKNOWN

    puts: list[int] = []
    calls: list[int] = []
    for s in snapshot.contracts:
        oi = s.open_interest
        if oi is None:
            return UNKNOWN
        if s.contract.right == OptionRight.put:
            puts.append(oi)
        else:
            calls.append(oi)

    if not puts or not calls:
        return UNKNOWN

    call_sum = _sum_ints(calls)
    if call_sum <= 0:
        return UNKNOWN

    put_sum = _sum_ints(puts)
    return _quantize(Decimal(put_sum) / Decimal(call_sum), PCR_QUANTUM)


def pcr_volume(snapshot: ChainSnapshot) -> Decimal | _Unknown:
    """
    Put/Call Volume ratio.

    v1.2-B policy:
    - requires snapshot quality_ok
    - requires volume on all contracts in the snapshot
    - requires at least one PUT and one CALL
    - denominator (CALL volume sum) must be > 0
    - result is quantized to PCR_QUANTUM
    """

    if not _ensure_metrics_allowed(snapshot):
        return UNKNOWN

    puts: list[int] = []
    calls: list[int] = []
    for s in snapshot.contracts:
        vol = s.volume
        if vol is None:
            return UNKNOWN
        if s.contract.right == OptionRight.put:
            puts.append(vol)
        else:
            calls.append(vol)

    if not puts or not calls:
        return UNKNOWN

    call_sum = _sum_ints(calls)
    if call_sum <= 0:
        return UNKNOWN

    put_sum = _sum_ints(puts)
    return _quantize(Decimal(put_sum) / Decimal(call_sum), PCR_QUANTUM)


def iv_skew(snapshot: ChainSnapshot) -> Decimal | _Unknown:
    """
    A minimal v1.2-B skew-style metric: mean(put_iv) - mean(call_iv).

    v1.2-B policy:
    - requires snapshot quality_ok
    - requires iv on all contracts in the snapshot
    - requires at least one PUT and one CALL
    - result is quantized to SKEW_QUANTUM
    """

    if not _ensure_metrics_allowed(snapshot):
        return UNKNOWN

    put_ivs: list[Decimal] = []
    call_ivs: list[Decimal] = []
    for s in snapshot.contracts:
        iv = s.iv
        if iv is None:
            return UNKNOWN
        if s.contract.right == OptionRight.put:
            put_ivs.append(iv)
        else:
            call_ivs.append(iv)

    if not put_ivs or not call_ivs:
        return UNKNOWN

    put_mean = sum(put_ivs) / Decimal(len(put_ivs))
    call_mean = sum(call_ivs) / Decimal(len(call_ivs))
    return _quantize(put_mean - call_mean, SKEW_QUANTUM)


def oi_change(prev: ChainSnapshot | None, curr: ChainSnapshot) -> Decimal | _Unknown:
    """
    Net chain open-interest change vs the immediately previous snapshot for the same chain identity.

    v1.2-B policy:
    - requires both snapshots quality_ok
    - requires identical contract-id sets between prev and curr (fail closed)
    - requires open_interest on all contracts in both snapshots
    - returns Decimal integer (no fractional)
    """

    if prev is None:
        return UNKNOWN
    if not _ensure_metrics_allowed(prev) or not _ensure_metrics_allowed(curr):
        return UNKNOWN

    prev_ids = tuple(s.contract.canonical_id() for s in prev.contracts)
    curr_ids = tuple(s.contract.canonical_id() for s in curr.contracts)
    if prev_ids != curr_ids:
        return UNKNOWN

    prev_sum = 0
    curr_sum = 0
    for ps, cs in zip(prev.contracts, curr.contracts, strict=True):
        poi = ps.open_interest
        coi = cs.open_interest
        if poi is None or coi is None:
            return UNKNOWN
        prev_sum += int(poi)
        curr_sum += int(coi)

    return Decimal(curr_sum - prev_sum)


def oi_change_puts(prev: ChainSnapshot | None, curr: ChainSnapshot) -> Decimal | _Unknown:
    if prev is None:
        return UNKNOWN
    if not _ensure_metrics_allowed(prev) or not _ensure_metrics_allowed(curr):
        return UNKNOWN
    prev_ids = tuple(s.contract.canonical_id() for s in prev.contracts)
    curr_ids = tuple(s.contract.canonical_id() for s in curr.contracts)
    if prev_ids != curr_ids:
        return UNKNOWN

    prev_sum = 0
    curr_sum = 0
    for ps, cs in zip(prev.contracts, curr.contracts, strict=True):
        if ps.contract.right != OptionRight.put:
            continue
        poi = ps.open_interest
        coi = cs.open_interest
        if poi is None or coi is None:
            return UNKNOWN
        prev_sum += int(poi)
        curr_sum += int(coi)
    return Decimal(curr_sum - prev_sum)


def oi_change_calls(prev: ChainSnapshot | None, curr: ChainSnapshot) -> Decimal | _Unknown:
    if prev is None:
        return UNKNOWN
    if not _ensure_metrics_allowed(prev) or not _ensure_metrics_allowed(curr):
        return UNKNOWN
    prev_ids = tuple(s.contract.canonical_id() for s in prev.contracts)
    curr_ids = tuple(s.contract.canonical_id() for s in curr.contracts)
    if prev_ids != curr_ids:
        return UNKNOWN

    prev_sum = 0
    curr_sum = 0
    for ps, cs in zip(prev.contracts, curr.contracts, strict=True):
        if ps.contract.right != OptionRight.call:
            continue
        poi = ps.open_interest
        coi = cs.open_interest
        if poi is None or coi is None:
            return UNKNOWN
        prev_sum += int(poi)
        curr_sum += int(coi)
    return Decimal(curr_sum - prev_sum)

