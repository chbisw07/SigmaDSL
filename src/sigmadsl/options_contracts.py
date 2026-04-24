from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .runtime_models import dec, dec_str


CANONICAL_OPTION_ID_PREFIX = "OPT"
STRIKE_QUANTUM = Decimal("0.01")


_SYM_RE = re.compile(r"^[A-Z0-9._-]{1,32}$")
_VENUE_RE = re.compile(r"^[A-Z0-9._-]{1,16}$")


class OptionRight(str, Enum):
    call = "CALL"
    put = "PUT"


def parse_option_right(text: str) -> OptionRight | None:
    """
    Parse an option right deterministically.

    Accepted tokens (case-insensitive):
    - CALL / PUT (canonical)
    - C / P
    - CE / PE (India market convention)
    """

    t = text.strip().upper()
    if t in ("CALL", "C", "CE"):
        return OptionRight.call
    if t in ("PUT", "P", "PE"):
        return OptionRight.put
    return None


def _validate_symbol(sym: str) -> bool:
    return bool(_SYM_RE.fullmatch(sym))


def _validate_venue(venue: str) -> bool:
    return bool(_VENUE_RE.fullmatch(venue))


def _parse_expiry(expiry: str) -> date | None:
    # Strict ISO date (YYYY-MM-DD). No guessing.
    try:
        return date.fromisoformat(expiry)
    except Exception:
        return None


def _parse_strike(strike: str) -> tuple[Decimal | None, str | None]:
    try:
        d = dec(strike)
    except Exception:
        return None, "Strike is not a valid decimal"
    if d <= 0:
        return None, "Strike must be > 0"
    # Reject more than 2 decimal places; do not guess.
    if abs(d.as_tuple().exponent) > 2:
        return None, "Strike must have at most 2 decimal places"
    return d.quantize(STRIKE_QUANTUM), None


@dataclass(frozen=True)
class OptionContract:
    """
    v1.1-A: minimal option contract identity.

    Not a broker symbol; this is a broker-agnostic canonical identity used for deterministic fixtures.
    """

    venue: str
    underlying: str
    expiry: date
    strike: Decimal
    right: OptionRight
    lot_size: int

    def canonical_id(self) -> str:
        strike_s = dec_str(self.strike)
        return f"{CANONICAL_OPTION_ID_PREFIX}:{self.venue}:{self.underlying}:{self.expiry.isoformat()}:{strike_s}:{self.right.value}:{self.lot_size}"


def parse_option_contract_id(
    text: str,
    *,
    file: Path | None = None,
    line: int | None = None,
    column: int | None = None,
) -> tuple[OptionContract | None, list[Diagnostic]]:
    """
    Parse and validate a canonical option contract id.

    Format (v1.1-A):
      OPT:<VENUE>:<UNDERLYING>:<EXPIRY>:<STRIKE>:<RIGHT>:<LOT>

    Example:
      OPT:NSE:TCS:2026-01-29:100:CALL:150
    """

    diags: list[Diagnostic] = []
    t = text.strip()

    parts = t.split(":")
    if len(parts) != 7:
        diags.append(
            diag(
                code="SD700",
                severity=Severity.error,
                message="Invalid option contract id (expected 7 ':'-separated fields: OPT:VENUE:UNDERLYING:EXPIRY:STRIKE:RIGHT:LOT)",
                file=file,
                line=line,
                column=column,
            )
        )
        return None, sorted(diags)

    prefix, venue, underlying, expiry_s, strike_s, right_s, lot_s = parts
    if prefix != CANONICAL_OPTION_ID_PREFIX:
        diags.append(
            diag(
                code="SD700",
                severity=Severity.error,
                message=f"Invalid option contract id prefix: expected {CANONICAL_OPTION_ID_PREFIX!r}",
                file=file,
                line=line,
                column=column,
            )
        )

    if not _validate_venue(venue):
        diags.append(
            diag(
                code="SD701",
                severity=Severity.error,
                message="Invalid venue (expected [A-Z0-9._-], length 1..16)",
                file=file,
                line=line,
                column=column,
            )
        )

    if not _validate_symbol(underlying):
        diags.append(
            diag(
                code="SD702",
                severity=Severity.error,
                message="Invalid underlying symbol (expected [A-Z0-9._-], length 1..32)",
                file=file,
                line=line,
                column=column,
            )
        )

    expiry = _parse_expiry(expiry_s)
    if expiry is None:
        diags.append(
            diag(
                code="SD703",
                severity=Severity.error,
                message="Invalid expiry (expected YYYY-MM-DD)",
                file=file,
                line=line,
                column=column,
            )
        )

    strike, strike_err = _parse_strike(strike_s)
    if strike is None:
        diags.append(
            diag(
                code="SD704",
                severity=Severity.error,
                message=f"Invalid strike: {strike_err}",
                file=file,
                line=line,
                column=column,
            )
        )

    right = parse_option_right(right_s)
    if right is None:
        diags.append(
            diag(
                code="SD705",
                severity=Severity.error,
                message="Invalid option right (expected CALL or PUT)",
                file=file,
                line=line,
                column=column,
            )
        )

    lot_size: int | None = None
    try:
        lot_size = int(lot_s)
    except Exception:
        diags.append(
            diag(
                code="SD706",
                severity=Severity.error,
                message="Invalid lot size (expected integer > 0)",
                file=file,
                line=line,
                column=column,
            )
        )
    else:
        if lot_size <= 0:
            diags.append(
                diag(
                    code="SD706",
                    severity=Severity.error,
                    message="Invalid lot size (expected integer > 0)",
                    file=file,
                    line=line,
                    column=column,
                )
            )

    if diags:
        return None, sorted(diags)

    assert expiry is not None and strike is not None and right is not None and lot_size is not None
    return (
        OptionContract(
            venue=venue,
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            right=right,
            lot_size=lot_size,
        ),
        [],
    )

