from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .options_snapshots import OptionSnapshot


@dataclass(frozen=True)
class OptionEvent:
    """
    v1.1-B: atomic option snapshot event (contract-level).

    The runner produces one event per CSV row after deterministic contract selection/filtering.
    """

    symbol: str  # canonical option contract id (OPT:...)
    index: int
    timestamp: str
    snapshot: OptionSnapshot
    underlying_price: Decimal | None = None  # selection helper reference; not part of snapshot semantics
    session_is_regular: bool = True
    underlying_return_5m: Decimal | None = None  # optional linkage for basic predicates

    def to_identity(self) -> dict:
        return {"symbol": self.symbol, "index": self.index, "timestamp": self.timestamp}
