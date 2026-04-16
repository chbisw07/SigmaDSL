from __future__ import annotations

from dataclasses import dataclass

from .types import (
    BOOL,
    DECIMAL,
    DURATION,
    INT,
    PRICE,
    PERCENT,
    QUANTITY,
    STRING,
    TIMESTAMP,
    Type,
)


@dataclass(frozen=True)
class VerbSignature:
    name: str
    required: dict[str, Type]
    optional: dict[str, Type]


@dataclass(frozen=True)
class FunctionSignature:
    name: str
    min_args: int
    max_args: int


def underlying_env_types() -> dict[str, Type]:
    """
    Minimal field/type environment for `underlying` context for v0.2-A.

    Source: docs/DSL_v0.md Chapter 12.2.2 (minimum set).
    """

    return {
        # series names used in historical functions (PROVISIONAL)
        "open": PRICE,
        "high": PRICE,
        "low": PRICE,
        "close": PRICE,
        "volume": QUANTITY,
        # dotted fields
        "bar.open": PRICE,
        "bar.high": PRICE,
        "bar.low": PRICE,
        "bar.close": PRICE,
        "bar.volume": QUANTITY,
        "bar.time": TIMESTAMP,
        "session.is_regular": BOOL,
        "data.is_fresh": BOOL,
        # used in examples (PROVISIONAL)
        "underlying.return_5m": PERCENT,
    }


def verb_signatures() -> dict[str, VerbSignature]:
    """
    Minimal verb signatures for v0.2-A (used for argument type checking).

    Kept intentionally small and extendable.
    """

    return {
        "emit_signal": VerbSignature(
            name="emit_signal",
            required={"kind": STRING},
            optional={
                "reason": STRING,
                "strength": DECIMAL,
            },
        ),
        "annotate": VerbSignature(
            name="annotate",
            required={"note": STRING},
            optional={},
        ),
    }


def function_names() -> set[str]:
    # Expression-call whitelist (pure/deterministic).
    #
    # v0.2: simple helpers for authoring + typing.
    # v0.5: adds indicator calls (EMA/RSI/ATR/VWAP) via deterministic registry.
    return {
        "abs",
        "highest",
        "lowest",
        "prior_high",
        "prior_low",
        # indicators (v0.5-A)
        "ema",
        "rsi",
        "atr",
        "vwap",
    }
