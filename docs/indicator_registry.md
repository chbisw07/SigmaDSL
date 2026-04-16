# SigmaDSL Indicators (v0.5-A)

This page documents the **implemented** indicator surface introduced in **Sprint 0.5-A**.

Principles:

- indicators are **pure** (no side effects)
- indicator semantics are **version-pinned** (see `docs/dsl_v0.5.md`)
- indicator outputs are **deterministic** and protected by numeric goldens

See also: `docs/indicator_cookbook.md` for worked patterns and runnable examples.

## Supported indicators

All indicators are called as expression functions in `when` conditions.

### `ema(series, length)`

- output type: `Price`
- `series`: bar-close series name (`close` or `bar.close`)
- `length`: `Int` (must be > 0)

### `rsi(series, length)`

- output type: `Percent` ratio in `[0, 1]`
- `series`: bar-close series name (`close` or `bar.close`)
- `length`: `Int` (must be > 0)

Note: compare to percent literals like `70%` (which is `0.7`).

### `atr(length)`

- output type: `Price`
- `length`: `Int` (must be > 0)
- uses `high/low/close` from the bar stream

### `vwap()` and `vwap(length)`

- output type: `Price`
- uses `close` as the price and `volume` as weights
- `vwap()` uses all bars up to the current bar
- `vwap(length)` uses the last `length` bars (partial if fewer)

## Deterministic window semantics (v0.5-A)

- alignment: bar-close aligned; window includes the current bar
- warmup: allowed; partial-history computation is deterministic
- rounding: indicator outputs are quantized to **8 decimal places**, rounding **half up**

## Example

```sr
rule "EQ: Trend Up" in underlying:
    when bar.close > ema(close, 20) and rsi(close, 14) > 60%:
        then emit_signal(kind="TREND_UP", reason="ema20_and_rsi14")
```
