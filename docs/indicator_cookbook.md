# Indicator cookbook (v0.5)

This cookbook shows **practical, implemented** indicator usage patterns in SigmaDSL as of **v0.5**.

Source of truth for semantics:
- `docs/dsl_v0.5.md` (spec snapshot)
- `docs/indicator_registry.md` (implemented surface)

Worked sample pack (rules + datasets + expected outputs):
- `examples/equity_indicator_rules/`

## Important semantics (v0.5-A pinned)

- Alignment: **bar-close** aligned; windows include the current bar.
- Warmup: **allowed** (partial history computes deterministically).
- Rounding: indicator outputs are quantized to **8 decimal places** (half-up).
- `rsi(...)` returns a `Percent` ratio in `[0, 1]`:
  - compare using percent literals like `70%` (`0.7`), not `70`.

## Common patterns

### 1) EMA trend filter (fast > slow)

```sr
rule "EMA Trend (5>10)" in underlying:
    when ema(close, 5) > ema(close, 10) and bar.close > ema(close, 10):
        then emit_signal(kind="EMA_TREND_UP", reason="ema5_gt_ema10")
```

### 2) VWAP bias (above VWAP lookback)

```sr
rule "Above VWAP(5)" in underlying:
    when bar.close > vwap(5):
        then emit_signal(kind="ABOVE_VWAP5", reason="close_gt_vwap5")
```

### 3) RSI mean reversion (overbought/oversold)

```sr
rule "RSI Oversold (5)" in underlying:
    when rsi(close, 5) < 30%:
        then emit_signal(kind="RSI_OVERSOLD", reason="rsi_lt_30pct")

rule "RSI Overbought (5)" in underlying:
    when rsi(close, 5) > 70%:
        then emit_signal(kind="RSI_OVERBOUGHT", reason="rsi_gt_70pct")
```

### 4) ATR volatility regime tagging

```sr
rule "ATR high-vol annotation (5)" in underlying:
    when atr(5) > 10:
        then annotate(note="atr_gt_10")
```

## Run the cookbook examples

Validate and lint the sample pack:

```bash
sigmadsl validate examples/equity_indicator_rules/
sigmadsl lint examples/equity_indicator_rules/
```

Run a pack and compare to expected outputs:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/ > out.jsonl
diff -u examples/equity_indicator_rules/expected/run_trend_following.jsonl out.jsonl
```

Replay is identical:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/ --log-out runlog.json > out.jsonl
sigmadsl replay --log runlog.json > replay.jsonl
diff -u out.jsonl replay.jsonl
```

## Lightweight pack introspection (v0.5-B)

Use `sigmadsl profile` to see which indicators/verbs/functions a pack references:

```bash
sigmadsl profile examples/equity_indicator_rules/packs/trend_following/
```

