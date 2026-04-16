# Equity indicator rules (v0.5-B)

This folder contains **indicator-based sample strategies** that run on the current SigmaDSL
single-symbol equity/bar runner.

Scope (v0.5):
- deterministic indicator calls: `ema`, `rsi`, `atr`, `vwap`
- deterministic windows (bar-close aligned; warmup allowed)
- deterministic run → log → replay workflow

## Layout

- `packs/` — example rule packs (each pack is a directory of `.sr` files)
- `data/` — small CSV bar series used by the packs
- `expected/` — expected `sigmadsl run` outputs (JSONL) for regression checking

## Quick commands

Validate everything:

```bash
sigmadsl validate examples/equity_indicator_rules/
sigmadsl lint examples/equity_indicator_rules/
```

Run the packs:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/
sigmadsl run --input examples/equity_indicator_rules/data/bars_reversion.csv --rules examples/equity_indicator_rules/packs/mean_reversion/
sigmadsl run --input examples/equity_indicator_rules/data/bars_volatility.csv --rules examples/equity_indicator_rules/packs/volatility_filters/
```

Replay a logged run:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/ --log-out runlog.json
sigmadsl replay --log runlog.json
```

## Notes

- **Warmup** is allowed: indicators compute deterministically on partial history until enough bars exist.
- `rsi(...)` returns a `Percent` ratio in `[0, 1]`, so compare against literals like `70%` (`0.7`).

