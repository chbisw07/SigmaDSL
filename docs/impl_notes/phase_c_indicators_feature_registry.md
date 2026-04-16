# Phase C — Indicators + Feature Registry (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md` (project plan / roadmap).  
This document accumulates engineering notes for Phase C sprints (v0.5+).

---

## Sprint 0.5-A — Indicator registry + caching

### Sprint goal

Ship the first deterministic, replay-safe indicator foundation:

- a small, explicit indicator registry with pinned versions
- deterministic window/alignment semantics
- deterministic rounding policy protected by numeric goldens
- per-run caching to avoid redundant recomputation (without changing semantics)
- integrate indicator calls into existing parse → typecheck → lint → run/replay pipeline

### What was implemented

- **Indicator registry + implementations**: `src/sigmadsl/indicators.py`
  - registry version: `0.5-a`
  - pinned indicator keys: `ema@1`, `rsi@1`, `atr@1`, `vwap@1`
  - indicator functions:
    - `ema(series, length)`
    - `rsi(series, length)` (returns a `Percent` ratio in `[0, 1]`)
    - `atr(length)` (uses `high/low/close`)
    - `vwap()` / `vwap(length)` (uses `close` + `volume`)
- **Rounding policy (pinned)**:
  - quantize indicator outputs to **8 decimal places**
  - rounding mode: **ROUND_HALF_UP**
- **Per-run caching**: `IndicatorCache`
  - key: `(indicator_key, params, event_index)`
  - deterministic and semantics-preserving (hits/misses are observable only in tests)
- **Runtime integration**: `src/sigmadsl/evaluator.py`
  - indicator calls are evaluated as whitelisted pure expression function calls
  - a fresh `IndicatorCache()` is created per `evaluate_underlying(...)` run
- **Lint whitelist**: `src/sigmadsl/builtins.py`
  - indicator function names are added to the allowed call surface for `sigmadsl lint`
- **Type checking**: `src/sigmadsl/typechecker.py`
  - validates indicator arity and `length` type (`Int`)
  - return types:
    - `ema` / `atr` / `vwap` → `Price`
    - `rsi` → `Percent`
- **Run log pinning**: `src/sigmadsl/runlog.py` + `src/sigmadsl/runner.py`
  - bumped run log schema version to `0.5-a`
  - logs include `indicators` metadata:
    - `registry_version`
    - `pinned[]`
    - `referenced[]` (computed from executed rules)
  - replay remains backward compatible with `0.4-a` logs (no indicators section)

### Deterministic semantics (v0.5-A)

Window/alignment policy:

- bar-close aligned; windows include the current bar
- warmup is allowed (partial history computes deterministically)

Indicator definitions are pinned by `name@version` keys and protected by numeric goldens.

### Tests + golden strategy

- Numeric goldens (strict to 8 decimal places):
  - `tests/golden/indicators_basic.json`
  - `tests/test_indicators_numeric.py`
- Type checking fixtures:
  - `tests/fixtures/typecheck/valid/ok_indicators_v0_5_a.sr`
  - `tests/fixtures/typecheck/invalid/bad_indicator_length_type.sr`
- End-to-end runner golden using indicators:
  - `tests/fixtures/eval/rules_indicators.sr`
  - `tests/golden/run_indicators.jsonl`
- Replay/log pinning assertions:
  - `tests/test_cli_replay.py`

### Commands to run

Run the full test suite:

```bash
pytest
```

Run only indicator tests:

```bash
pytest -k indicators
```

Manual demo:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_indicators.sr
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_indicators.sr --log-out runlog.json
sigmadsl replay --log runlog.json
```

### Known limitations (intentionally deferred)

- no broader indicator catalog beyond EMA/RSI/ATR/VWAP
- no multi-symbol histories or cross-symbol feature aggregation
- no explicit missing/unknown three-valued logic
- no imports/packaging of indicator libraries (Phase D / later)

---

## Sprint 0.5-B — Indicator-based sample strategies

### Sprint goal

Turn the v0.5-A indicator foundation into a user-runnable product slice:

- realistic indicator-based sample packs
- small CSV datasets and deterministic expected outputs
- end-to-end tests proving indicator-driven run/replay determinism
- practical documentation (cookbook)
- lightweight pack introspection (`sigmadsl profile`)

### What was implemented

- **Indicator sample packs**: `examples/equity_indicator_rules/`
  - packs:
    - `packs/trend_following/` (EMA + VWAP + RSI note)
    - `packs/mean_reversion/` (RSI thresholds + VWAP3 reversion)
    - `packs/volatility_filters/` (ATR regimes + ATR-capped breakout)
  - datasets: `examples/equity_indicator_rules/data/*.csv`
  - expected outputs: `examples/equity_indicator_rules/expected/*.jsonl`
- **End-to-end tests**:
  - validate/lint the example directory
  - run packs and compare stdout to expected JSONL
  - replay equivalence on an indicator-driven pack
  - `tests/test_examples_indicator_rules_pack.py`
- **Pack introspection command**: `sigmadsl profile`
  - summarizes:
    - `indicators.referenced` (pinned keys like `ema@1`)
    - expression function calls
    - verbs used
  - deterministic JSON output suitable for golden tests
  - `src/sigmadsl/profile.py`
- **Documentation**:
  - cookbook: `docs/indicator_cookbook.md`
  - updated high-level v0.5 summary: `docs/high_level_dsl_v0.5.md`
  - updated quickstart and README to point to the sample pack

### Commands to run

Validate and run the indicator examples:

```bash
sigmadsl validate examples/equity_indicator_rules/
sigmadsl lint examples/equity_indicator_rules/
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/
```

Profile a pack:

```bash
sigmadsl profile examples/equity_indicator_rules/packs/trend_following/
```

Replay equivalence:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/ --log-out runlog.json > out.jsonl
sigmadsl replay --log runlog.json > replay.jsonl
diff -u out.jsonl replay.jsonl
```

### Known limitations (intentionally deferred)

- these are sample strategies only; no position management or execution planning exists
- indicators remain limited to EMA/RSI/ATR/VWAP
- multi-symbol evaluation remains deferred
