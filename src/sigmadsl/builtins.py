from __future__ import annotations

from dataclasses import dataclass

from .types import (
    BOOL,
    DECIMAL,
    DATE,
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


def option_env_types() -> dict[str, Type]:
    """
    Minimal field/type environment for `option` context for v1.1-A.

    Source: docs/DSL_v0.md Chapter 12.2.2 (intended option fields; v1.1+).

    Note: this is type checking only; runtime `run` support for option snapshots is delivered later (v1.1-B).
    """

    return {
        # option contract identity fields
        "option.contract_id": STRING,
        "option.strike": PRICE,
        "option.expiry": DATE,
        "option.type": STRING,  # canonical right is CALL/PUT; represented as String in DSL for now
        "option.lot": QUANTITY,
        # option snapshot fields (atomic)
        "option.bid": PRICE,
        "option.ask": PRICE,
        "option.last": PRICE,
        "option.close": PRICE,
        "option.iv": PERCENT,
        "option.delta": DECIMAL,
        "option.gamma": DECIMAL,
        "option.theta": DECIMAL,
        "option.vega": DECIMAL,
        # guards
        "session.is_regular": BOOL,
        "data.is_fresh": BOOL,
        # allow limited underlying linkage fields used in deferred examples
        "underlying.return_5m": PERCENT,
    }


def chain_env_types() -> dict[str, Type]:
    """
    Sprint v1.2-A: minimal field/type environment for `chain` context.

    Scope: chain snapshot quality/atomicity predicates only (no analytics).
    """

    return {
        # Timestamp identity for the atomic snapshot event.
        # `chain.as_of` matches the DSL_v0 terminology; `chain.time` is kept as a stable alias.
        "chain.as_of": TIMESTAMP,
        "chain.time": TIMESTAMP,
        "chain.is_fresh": BOOL,
        "chain.is_complete": BOOL,
        "chain.has_unknowns": BOOL,
        "chain.quality_ok": BOOL,
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
        # v1.0-A: intent profile verbs (outputs only; no planning semantics yet).
        "declare_intent": VerbSignature(
            name="declare_intent",
            required={"kind": STRING},
            optional={
                "quantity": QUANTITY,
                "percent": PERCENT,
                "reason": STRING,
            },
        ),
        "cancel_intent": VerbSignature(
            name="cancel_intent",
            required={},
            optional={
                "reason": STRING,
            },
        ),
        # v1.0-A: risk profile verbs (constraint outputs only; no enforcement semantics yet).
        "constrain_max_position": VerbSignature(
            name="constrain_max_position",
            required={"quantity": QUANTITY},
            optional={
                "reason": STRING,
            },
        ),
        "block": VerbSignature(
            name="block",
            required={"reason": STRING},
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
