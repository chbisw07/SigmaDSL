from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from . import ast
from .expr import Call, ExprNode, dotted_name
from .runtime_models import UnderlyingEvent, dec, dec_str


INDICATOR_REGISTRY_VERSION = "0.5-a"


@dataclass(frozen=True)
class IndicatorId:
    name: str
    version: str

    def key(self) -> str:
        return f"{self.name}@{self.version}"


@dataclass(frozen=True)
class IndicatorDef:
    """
    Deterministic indicator definition entry.

    - `name` matches the expression function name (e.g., `ema`).
    - `version` pins semantics and rounding behavior.
    """

    id: IndicatorId
    params: tuple[str, ...]
    output: str  # "Price" | "Percent" (v0.5-A)


def indicator_registry() -> dict[str, IndicatorDef]:
    """
    v0.5-A deterministic indicator registry.

    Registry is intentionally explicit and static (no plugins in v0.5-A).
    """

    defs = [
        IndicatorDef(id=IndicatorId("ema", "1"), params=("series", "length"), output="Price"),
        IndicatorDef(id=IndicatorId("rsi", "1"), params=("series", "length"), output="Percent"),
        IndicatorDef(id=IndicatorId("atr", "1"), params=("length",), output="Price"),
        # v0.5-A: accept vwap() and vwap(length)
        IndicatorDef(id=IndicatorId("vwap", "1"), params=("length?",), output="Price"),
    ]
    return {d.id.name: d for d in defs}


def pinned_indicator_keys() -> tuple[str, ...]:
    """
    Indicator versions are part of the deterministic engine contract and should be recorded in logs.
    """

    regs = indicator_registry()
    return tuple(sorted(d.id.key() for d in regs.values()))


def referenced_indicator_keys(sf: ast.SourceFile) -> set[str]:
    """
    Deterministically collect which pinned indicator versions are referenced by a source file.

    v0.5-A: indicator calls appear as expression function calls (e.g., ema(close, 20)).
    """

    regs = indicator_registry()
    referenced: set[str] = set()

    def walk(node: ExprNode | None):
        if node is None:
            return
        if isinstance(node, Call):
            fn = dotted_name(node.func)
            if fn is not None and fn in regs:
                referenced.add(regs[fn].id.key())
            for a in node.args:
                walk(a)
            for _, v in node.kwargs:
                walk(v)
            return
        for child in getattr(node, "__dict__", {}).values():
            if isinstance(child, ExprNode):
                walk(child)
            elif isinstance(child, tuple):
                for item in child:
                    if isinstance(item, ExprNode):
                        walk(item)
                    elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], ExprNode):
                        walk(item[1])

    for rule in sf.rules:
        for branch in rule.branches:
            if branch.condition is not None:
                walk(branch.condition.node)
            for then_line in branch.actions:
                for arg in then_line.call.args:
                    walk(arg.value.node)

    return referenced


def quantize_indicator(value: Decimal) -> Decimal:
    """
    v0.5-A: stable indicator output rounding policy for goldens.

    - Uses Decimal with explicit quantize to 8 decimal places.
    - Rounding: ROUND_HALF_UP.
    """

    q = Decimal("0.00000001")
    return value.quantize(q, rounding=ROUND_HALF_UP)


def ema(series: list[Decimal], length: int) -> Decimal:
    """
    EMA v1 (pinned):
    - k = 2 / (length + 1)
    - seed = first value in the window
    - window is aligned to bar-close and includes the current bar
    - if insufficient history, compute over available values (partial window)
    """

    if length <= 0:
        raise ValueError("ema length must be positive")
    if not series:
        raise ValueError("ema requires at least one value")
    k = Decimal(2) / (Decimal(length) + Decimal(1))
    e = series[0]
    for v in series[1:]:
        e = (v - e) * k + e
    return quantize_indicator(e)


def rsi(series: list[Decimal], length: int) -> Decimal:
    """
    RSI v1 (pinned) as a Percent ratio in [0, 1].

    v0.5-A semantics:
    - aligned to bar-close; uses consecutive differences over the window
    - window includes the current bar
    - if insufficient history, compute over available diffs
    - if avg_gain == 0 and avg_loss == 0 => 0.5
    - if avg_loss == 0 => 1.0
    - if avg_gain == 0 => 0.0
    """

    if length <= 0:
        raise ValueError("rsi length must be positive")
    if len(series) < 2:
        return quantize_indicator(Decimal("0.5"))

    diffs = [series[i] - series[i - 1] for i in range(1, len(series))]
    # Use up to (length-1) diffs; if fewer, compute partial.
    window_diffs = diffs[-max(1, min(len(diffs), length - 1)) :]

    gains = [d for d in window_diffs if d > 0]
    losses = [-d for d in window_diffs if d < 0]

    avg_gain = sum(gains, Decimal(0)) / Decimal(len(window_diffs))
    avg_loss = sum(losses, Decimal(0)) / Decimal(len(window_diffs))

    if avg_gain == 0 and avg_loss == 0:
        return quantize_indicator(Decimal("0.5"))
    if avg_loss == 0:
        return quantize_indicator(Decimal("1"))
    if avg_gain == 0:
        return quantize_indicator(Decimal("0"))

    rs = avg_gain / avg_loss
    rsi_0_100 = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
    return quantize_indicator(rsi_0_100 / Decimal(100))


def atr(high: list[Decimal], low: list[Decimal], close: list[Decimal], length: int) -> Decimal:
    """
    ATR v1 (pinned) using simple moving average of True Range (TR).

    - aligned to bar-close
    - window includes the current bar
    - TR for bar i:
        max(high-low, abs(high-prev_close), abs(low-prev_close))
      with prev_close = close[i-1] (for i==0, prev_close=close[0]).
    - if insufficient history, compute SMA over available TRs (partial window)
    """

    if length <= 0:
        raise ValueError("atr length must be positive")
    if not high or not low or not close:
        raise ValueError("atr requires non-empty series")
    if not (len(high) == len(low) == len(close)):
        raise ValueError("atr series length mismatch")

    trs: list[Decimal] = []
    prev_close = close[0]
    for i in range(len(close)):
        h = high[i]
        l = low[i]
        c_prev = prev_close if i > 0 else close[0]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
        prev_close = close[i]

    window = trs[-min(length, len(trs)) :]
    atr_v = sum(window, Decimal(0)) / Decimal(len(window))
    return quantize_indicator(atr_v)


def vwap(close: list[Decimal], volume: list[Decimal], length: int | None) -> Decimal:
    """
    VWAP v1 (pinned) over a deterministic window.

    v0.5-A:
    - vwap() uses all available bars up to current event
    - vwap(length) uses the last N bars (partial if fewer)
    - price used: close
    - if sum(volume) == 0, returns the last close
    """

    if not close or not volume:
        raise ValueError("vwap requires non-empty series")
    if len(close) != len(volume):
        raise ValueError("vwap series length mismatch")
    if length is not None and length <= 0:
        raise ValueError("vwap length must be positive")

    n = len(close) if length is None else min(length, len(close))
    c = close[-n:]
    v = volume[-n:]
    denom = sum(v, Decimal(0))
    if denom == 0:
        return quantize_indicator(c[-1])
    num = sum((c[i] * v[i] for i in range(n)), Decimal(0))
    return quantize_indicator(num / denom)


class IndicatorCache:
    """
    Per-run deterministic indicator cache.

    Keyed by:
    - indicator key (name@version)
    - params tuple
    - event index
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, tuple[object, ...], int], Decimal] = {}
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def get_or_compute(
        self,
        *,
        indicator_key: str,
        params: tuple[object, ...],
        event_index: int,
        compute: Callable[[], Decimal],
    ) -> Decimal:
        k = (indicator_key, params, event_index)
        if k in self._cache:
            self._hits += 1
            return self._cache[k]
        self._misses += 1
        v = compute()
        self._cache[k] = v
        return v


def series_from_history(history: list[UnderlyingEvent], series_name: str) -> list[Decimal]:
    """
    Extract a numeric series from UnderlyingEvent history.
    Accepts both plain and dotted names (e.g., 'close' or 'bar.close').
    """

    if series_name.startswith("bar."):
        series_name = series_name.split(".", 1)[1]
    out: list[Decimal] = []
    for ev in history:
        b = ev.bar
        if series_name == "open":
            out.append(b.open)
        elif series_name == "high":
            out.append(b.high)
        elif series_name == "low":
            out.append(b.low)
        elif series_name == "close":
            out.append(b.close)
        elif series_name == "volume":
            out.append(b.volume)
        else:
            raise ValueError(f"Unknown series name: {series_name!r}")
    return out


def indicator_value_str(v: Decimal) -> str:
    return dec_str(v)
