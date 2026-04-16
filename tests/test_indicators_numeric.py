import json
from pathlib import Path

from sigmadsl.indicators import IndicatorCache, atr, ema, indicator_registry, rsi, series_from_history, vwap
from sigmadsl.runtime_models import Bar, UnderlyingEvent, dec


def _load_events(path: Path) -> list[UnderlyingEvent]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    events: list[UnderlyingEvent] = []
    for i, r in enumerate(rows):
        bar = Bar.from_dict(r)
        symbol = str(r.get("symbol", "TEST"))
        uret = r.get("underlying_return_5m")
        events.append(
            UnderlyingEvent(
                symbol=symbol,
                index=i,
                bar=bar,
                underlying_return_5m=dec(uret) if uret is not None else None,
            )
        )
    return events


def _q8(v) -> str:
    # v0.5-A pins indicator rounding to 8 decimal places; keep goldens strict.
    return format(v, "f")


def _computed_vectors() -> dict:
    basic = _load_events(Path("tests/fixtures/eval/bars_basic.json"))
    percent = _load_events(Path("tests/fixtures/eval/bars_percent.json"))

    out: dict[str, dict[str, list[str]]] = {"bars_basic": {}, "bars_percent": {}}

    # bars_basic vectors
    ema_3: list[str] = []
    rsi_3: list[str] = []
    atr_3: list[str] = []
    vwap_all: list[str] = []
    vwap_2: list[str] = []
    for i in range(len(basic)):
        hist = basic[: i + 1]
        close = series_from_history(hist, "close")
        volume = series_from_history(hist, "volume")
        high = series_from_history(hist, "high")
        low = series_from_history(hist, "low")
        ema_3.append(_q8(ema(close, 3)))
        rsi_3.append(_q8(rsi(close, 3)))
        atr_3.append(_q8(atr(high, low, close, 3)))
        vwap_all.append(_q8(vwap(close, volume, None)))
        vwap_2.append(_q8(vwap(close, volume, 2)))

    out["bars_basic"]["ema(close,3)"] = ema_3
    out["bars_basic"]["rsi(close,3)"] = rsi_3
    out["bars_basic"]["atr(3)"] = atr_3
    out["bars_basic"]["vwap()"] = vwap_all
    out["bars_basic"]["vwap(2)"] = vwap_2

    # bars_percent vectors (RSI only: include gains and losses)
    rsi_p: list[str] = []
    for i in range(len(percent)):
        hist = percent[: i + 1]
        close = series_from_history(hist, "close")
        rsi_p.append(_q8(rsi(close, 3)))
    out["bars_percent"]["rsi(close,3)"] = rsi_p

    return out


def test_indicators_numeric_golden_vectors():
    got = _computed_vectors()
    golden = Path("tests/golden/indicators_basic.json").read_text(encoding="utf-8")
    assert json.dumps(got, sort_keys=True, indent=2) + "\n" == golden


def test_indicator_cache_is_deterministic_for_repeated_calls():
    events = _load_events(Path("tests/fixtures/eval/bars_basic.json"))
    regs = indicator_registry()
    ema_key = regs["ema"].id.key()

    cache = IndicatorCache()

    def compute_for(i: int):
        hist = events[: i + 1]
        close = series_from_history(hist, "close")
        return ema(close, 3)

    for i in range(len(events)):
        cache.get_or_compute(
            indicator_key=ema_key,
            params=("close", 3),
            event_index=i,
            compute=lambda i=i: compute_for(i),
        )

    for i in range(len(events)):
        cache.get_or_compute(
            indicator_key=ema_key,
            params=("close", 3),
            event_index=i,
            compute=lambda i=i: compute_for(i),
        )

    assert cache.misses == len(events)
    assert cache.hits == len(events)

