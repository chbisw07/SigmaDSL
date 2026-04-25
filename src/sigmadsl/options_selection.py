from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .options_contracts import OptionContract, OptionRight


@dataclass(frozen=True)
class OptionSelectionRequest:
    """
    Sprint v1.1-C: deterministic contract selection over explicit option snapshots.

    Selection is performed once per run using a single "selection timestamp" snapshot row set.
    The runner then evaluates the selected contract's snapshot series as an atomic option context stream.
    """

    kind: str  # "atm" | "otm" | "delta"
    right: OptionRight | None = None
    expiry: str | None = None  # YYYY-MM-DD
    otm_rank: int = 1
    target_delta: Decimal | None = None


@dataclass(frozen=True)
class OptionSelectionCandidate:
    contract: OptionContract
    canonical_id: str
    underlying_price: Decimal | None
    delta: Decimal | None


def _right_order(r: OptionRight) -> int:
    return 0 if r == OptionRight.call else 1


def select_contract_id(
    *,
    req: OptionSelectionRequest,
    candidates: list[OptionSelectionCandidate],
    file: Path | None = None,
    line: int | None = None,
    column: int | None = None,
) -> tuple[str | None, list[Diagnostic]]:
    """
    Deterministically choose a single contract id from a set of candidates.

    Tie-breakers (deterministic):
    1) primary distance metric (abs strike distance / OTM distance / delta distance)
    2) earlier expiry
    3) right order (CALL before PUT)
    4) canonical contract id lexical order
    """

    kind = req.kind.strip().lower()
    diags: list[Diagnostic] = []

    if kind not in ("atm", "otm", "delta"):
        return None, [
            diag(
                code="SD740",
                severity=Severity.error,
                message=f"Unsupported selection kind: {req.kind!r} (expected 'atm', 'otm', or 'delta')",
                file=file,
                line=line,
                column=column,
            )
        ]

    filtered = candidates
    if req.right is not None:
        filtered = [c for c in filtered if c.contract.right == req.right]
    if req.expiry is not None:
        filtered = [c for c in filtered if c.contract.expiry.isoformat() == req.expiry]

    if kind == "otm" and req.right is None:
        return None, [
            diag(
                code="SD741",
                severity=Severity.error,
                message="OTM selection requires an explicit right filter (--right CALL|PUT)",
                file=file,
                line=line,
                column=column,
            )
        ]

    if not filtered:
        return None, [
            diag(
                code="SD748",
                severity=Severity.error,
                message="Selection has no candidates after applying filters",
                file=file,
                line=line,
                column=column,
            )
        ]

    if kind in ("atm", "otm"):
        if any(c.underlying_price is None for c in filtered):
            return None, [
                diag(
                    code="SD742",
                    severity=Severity.error,
                    message="ATM/OTM selection requires underlying_price to be present on all candidate rows",
                    file=file,
                    line=line,
                    column=column,
                )
            ]
        prices = sorted({c.underlying_price for c in filtered if c.underlying_price is not None})
        if len(prices) != 1:
            return None, [
                diag(
                    code="SD743",
                    severity=Severity.error,
                    message="ATM/OTM selection requires a single deterministic underlying_price on candidate rows",
                    file=file,
                    line=line,
                    column=column,
                )
            ]
        underlying_price = prices[0]

        if kind == "atm":
            ranked = sorted(
                filtered,
                key=lambda c: (
                    abs(c.contract.strike - underlying_price),
                    c.contract.expiry.isoformat(),
                    _right_order(c.contract.right),
                    c.canonical_id,
                ),
            )
            return ranked[0].canonical_id, []

        # otm
        assert req.right is not None
        if req.otm_rank < 1:
            return None, [
                diag(
                    code="SD744",
                    severity=Severity.error,
                    message="OTM rank must be >= 1",
                    file=file,
                    line=line,
                    column=column,
                )
            ]
        if req.right == OptionRight.call:
            otm = [c for c in filtered if c.contract.strike > underlying_price]
            ranked = sorted(
                otm,
                key=lambda c: (
                    c.contract.strike - underlying_price,
                    c.contract.expiry.isoformat(),
                    c.canonical_id,
                ),
            )
        else:
            otm = [c for c in filtered if c.contract.strike < underlying_price]
            ranked = sorted(
                otm,
                key=lambda c: (
                    underlying_price - c.contract.strike,
                    c.contract.expiry.isoformat(),
                    c.canonical_id,
                ),
            )
        if len(ranked) < req.otm_rank:
            return None, [
                diag(
                    code="SD745",
                    severity=Severity.error,
                    message=f"Not enough OTM candidates for rank {req.otm_rank} (got {len(ranked)})",
                    file=file,
                    line=line,
                    column=column,
                )
            ]
        return ranked[req.otm_rank - 1].canonical_id, []

    # delta selection
    if req.target_delta is None:
        return None, [
            diag(
                code="SD746",
                severity=Severity.error,
                message="Delta selection requires --target-delta",
                file=file,
                line=line,
                column=column,
            )
        ]

    delta_candidates = [c for c in filtered if c.delta is not None]
    if not delta_candidates:
        return None, [
            diag(
                code="SD747",
                severity=Severity.error,
                message="Delta selection requires delta to be present on candidate rows",
                file=file,
                line=line,
                column=column,
            )
        ]

    target = req.target_delta
    ranked = sorted(
        delta_candidates,
        key=lambda c: (
            abs(c.delta - target),  # type: ignore[operator]
            c.contract.expiry.isoformat(),
            _right_order(c.contract.right),
            c.canonical_id,
        ),
    )
    return ranked[0].canonical_id, diags
