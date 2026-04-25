from __future__ import annotations

from dataclasses import dataclass

from .options_snapshots import OptionSnapshot


CHAIN_SNAPSHOT_SCHEMA = "sigmadsl.chain_snapshot"
CHAIN_SNAPSHOT_SCHEMA_VERSION = "1.2-a"


@dataclass(frozen=True)
class ChainSnapshot:
    """
    Sprint v1.2-A: atomic option chain snapshot.

    The chain snapshot is a single coherent unit at a single snapshot timestamp, containing
    multiple per-contract atomic OptionSnapshot entries.
    """

    timestamp: str
    venue: str
    underlying: str
    expiries: tuple[str, ...]  # ISO dates (sorted unique)
    contracts: tuple[OptionSnapshot, ...]  # sorted by contract_id
    data_is_fresh: bool
    quality_flags: tuple[str, ...]  # sorted unique union
    is_complete: bool
    has_unknowns: bool

    def to_dict(self) -> dict:
        return {
            "schema": CHAIN_SNAPSHOT_SCHEMA,
            "schema_version": CHAIN_SNAPSHOT_SCHEMA_VERSION,
            "timestamp": self.timestamp,
            "venue": self.venue,
            "underlying": self.underlying,
            "expiries": list(self.expiries),
            "data_is_fresh": self.data_is_fresh,
            "quality_flags": list(self.quality_flags),
            "is_complete": self.is_complete,
            "has_unknowns": self.has_unknowns,
            "contracts": [c.to_dict() for c in self.contracts],
        }

