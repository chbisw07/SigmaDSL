from __future__ import annotations

from dataclasses import dataclass

from .chain_snapshots import ChainSnapshot


@dataclass(frozen=True)
class ChainEvent:
    """
    Sprint v1.2-A: chain snapshot event.

    A run evaluates a sequence of atomic ChainSnapshot events, ordered by timestamp.
    """

    symbol: str  # CHAIN:<VENUE>:<UNDERLYING>
    index: int
    timestamp: str
    snapshot: ChainSnapshot

    def to_identity(self) -> dict:
        return {"symbol": self.symbol, "index": self.index, "timestamp": self.timestamp}

