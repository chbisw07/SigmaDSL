# SigmaDSL — High-level DSL v0.5

Status: Implemented (indicator registry + deterministic indicator semantics).  
Scope: **Sprint 0.5-A** (“Indicator registry + caching”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.4.md`: v0.4 snapshot (run logs + replay + diff + explain workflow)
- `docs/dsl_v0.5.md`: spec snapshot for v0.5 (copy-forward with indicator/run-log chapters concretized)

This document describes what is **new** at the **v0.5 boundary**, based on implemented behavior in the repo.

## What v0.5 adds (Sprint 0.5-A)

v0.5 introduces the first deterministic indicator surface:

- a small, explicit, deterministic **indicator registry**
- **pinned indicator versions** recorded in run logs (replay-safe provenance)
- deterministic **window/alignment semantics** for indicator computation
- deterministic **rounding policy** for indicator outputs (numeric goldens protect it)
- per-run deterministic caching to avoid redundant recomputation (does not change semantics)

## Supported indicator calls (v0.5-A)

Indicators are called as pure expression functions inside `when` conditions:

- `ema(series, length)`
- `rsi(series, length)` (returns a `Percent` ratio in `[0, 1]`)
- `atr(length)` (uses the bar’s `high/low/close`)
- `vwap()` / `vwap(length)` (uses `close` + `volume`)

## Deterministic semantics (v0.5-A)

- **Alignment**: bar-close aligned; the window includes the current bar.
- **Warmup**: allowed; indicators compute deterministically over partial history when insufficient bars exist.
- **Rounding**: indicator outputs are quantized to **8 decimal places** (half-up), pinned as part of the engine contract.

## Run logs and replay (v0.5-A)

`sigmadsl run --log-out ...` now emits a run log schema that includes indicator pins:

- schema: `sigmadsl.runlog`
- schema_version: `0.5-a`
- `indicators.pinned[]`: all indicator versions shipped by the engine
- `indicators.referenced[]`: which pinned indicator versions were referenced by the executed rules

Replay remains self-contained and deterministic for the current equity/bar runner.

## Known limitations / deferred items

- single-symbol runner only (multi-symbol is deferred)
- indicator catalog is intentionally small (EMA/RSI/ATR/VWAP only)
- missing/unknown three-valued logic is still TBD in the base spec
- imports/packaging, options/chain, planning/risk remain out of scope

## Version summary (what changed in v0.5)

- added deterministic indicator registry + per-run caching
- added EMA/RSI/ATR/VWAP with pinned semantics + numeric goldens
- bumped run log schema to include indicator pin metadata (`sigmadsl.runlog` `0.5-a`)

