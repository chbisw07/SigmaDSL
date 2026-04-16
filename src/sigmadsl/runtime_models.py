from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def dec(value: str | int | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def dec_str(value: Decimal) -> str:
    """
    Stable, non-scientific string form for golden tests.
    """

    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".") or "0"
    return s


@dataclass(frozen=True)
class Bar:
    timestamp: str  # ISO-like string; v0.3-A treats this as an opaque identity
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @staticmethod
    def from_dict(d: dict) -> "Bar":
        return Bar(
            timestamp=str(d["timestamp"]),
            open=dec(d["open"]),
            high=dec(d["high"]),
            low=dec(d["low"]),
            close=dec(d["close"]),
            volume=dec(d.get("volume", "0")),
        )


@dataclass(frozen=True)
class UnderlyingEvent:
    """
    Minimal equity/bar event for Sprint 0.3-A.

    Only fields required by current DSL examples/type environment are included.
    """

    symbol: str
    index: int
    bar: Bar
    data_is_fresh: bool = True
    session_is_regular: bool = True
    underlying_return_5m: Decimal | None = None  # used in examples (PROVISIONAL)

    def to_identity(self) -> dict:
        return {
            "symbol": self.symbol,
            "index": self.index,
            "timestamp": self.bar.timestamp,
        }

