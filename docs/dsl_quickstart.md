# SigmaDSL Quickstart (v0.5-A)

This quickstart covers early **Phase A + Phase B** sprints:

- **Sprint 0.1-A**: parsing + deterministic diagnostics
- **Sprint 0.1-B**: sample pack + docs
- **Sprint 0.2-A**: type checker v1 (comparisons/boolean ops/verb argument types)
- **Sprint 0.2-B**: lint guardrails (forbidden constructs + signal-profile compliance)
- **Sprint 0.3-A**: deterministic evaluator + trace
- **Sprint 0.3-B**: `sigmadsl run` + JSON/JSONL decisions + basic explain
- **Sprint 0.4-A**: replayable run logs + `sigmadsl replay`
- **Sprint 0.4-B**: improved explain + `sigmadsl diff` + golden suite hardening
- **Sprint 0.5-A**: indicator registry + deterministic windows (EMA/RSI/ATR/VWAP)

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Write a minimal rule file

Create `basic.sr`:

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

## Validate it

```bash
sigmadsl validate basic.sr
```

Expected output:

```
OK
```

## Lint guardrails (v0.2-B)

Run lint to enforce “Python-shaped but not Python” guardrails:

```bash
sigmadsl lint basic.sr
```

Expected output:

```text
OK
```

## Try the sample pack (v0.1-B)

Sprint v0.1-B ships a starter sample pack under `examples/`:

```bash
sigmadsl validate examples/equity_min_rules/
```

Expected output:

```text
OK
```

## What `validate` checks in v0.1-A

- indentation-sensitive blocks (`rule` → branch → `then` lines)
- required structure:
  - `rule "<name>" in <context>:`
  - `when <expr>:` (with optional `elif` / `else`)
  - one or more `then <verb_call(...)>` lines under each branch
- deterministic diagnostics with: file, line, column, code, severity, message

## Type checking (v0.2-A)

`sigmadsl validate` also runs a conservative v1 type checker:

- conditions must type as `Bool`
- boolean operators (`and`/`or`/`not`) require boolean operands
- comparisons require compatible types (e.g., `Price` vs `Price`, `Percent` vs `Percent`)
- verb calls (`then ...`) have typed argument checks for a minimal verb set

Example type error:

```sr
rule "EQ: Bad" in underlying:
    when bar.close:
        then emit_signal(kind="X", reason="should_fail")
```

```text
... SD300 error: Type mismatch in condition: expected Bool, got Price
```

## Language guardrails (v0.2-B)

See `docs/language_guardrails.md` for a concise explanation of:

- forbidden constructs (assignments, loops, function defs),
- function-call whitelist rules,
- profile compliance (signal-only in v0.2).

## Limitations (intentional, for later sprints)

- multi-symbol evaluation is deferred (runner is single-symbol only)
- expression/function and verb signature sets are intentionally minimal and will expand later
- no imports/packaging, options/chain, planning/risk

## Deterministic evaluation + trace (v0.3-A)

Sprint 0.3-A ships a minimal evaluator for in-memory equity/bar events, verified via fixtures and goldens.

Run evaluator tests:

```bash
pytest -k evaluator
```

The golden-driven evaluator examples live under:

- `tests/fixtures/eval/` (rules + bar series)
- `tests/golden/eval_*.json` (expected deterministic decisions + trace)

## CLI runner (v0.3-B)

Sprint 0.3-B adds a minimal runner from CSV bars to JSON decisions:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

Default output format is JSONL (one decision per line). Redirect to a file if desired:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr > decisions.jsonl
```

Explain a decision (re-runs deterministically and prints the emitting rule trace):

```bash
sigmadsl explain --decision-id D0003 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

Explain a rule that didn’t fire at an event:

```bash
sigmadsl explain --rule "EQ: Breakout" --event-index 0 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

CSV requirements (v0.3-B):

- required columns: `symbol,timestamp,open,high,low,close,volume`
- optional columns: `underlying_return_5m,data_is_fresh,session_is_regular`
- single symbol only (multi-symbol series is deferred)

## Replay logs (v0.4-A)

Write a self-contained replay log:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr --log-out runlog.json
```

Replay it deterministically (output should match the original `run` output exactly):

```bash
sigmadsl replay --log runlog.json
```

Diff two run logs (v0.4-B):

```bash
sigmadsl diff run_a.json run_b.json
```

See `docs/debugging_determinism.md` for a concise debugging workflow.

## Indicators (v0.5-A)

v0.5-A introduces a small deterministic indicator surface (see `docs/indicator_registry.md`):

- `ema(series, length)`
- `rsi(series, length)` (returns a `Percent` ratio in `[0, 1]`)
- `atr(length)`
- `vwap()` / `vwap(length)`

Example:

```sr
rule "EQ: Trend Up" in underlying:
    when bar.close > ema(close, 20) and rsi(close, 14) > 60%:
        then emit_signal(kind="TREND_UP", reason="ema20_and_rsi14")
```

## Indicator sample packs (v0.5-B)

Runnable example packs live under:

- `examples/equity_indicator_rules/`

Validate + lint:

```bash
sigmadsl validate examples/equity_indicator_rules/
sigmadsl lint examples/equity_indicator_rules/
```

Run a pack and compare output:

```bash
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/ > out.jsonl
diff -u examples/equity_indicator_rules/expected/run_trend_following.jsonl out.jsonl
```

See `docs/indicator_cookbook.md` for worked patterns and runnable commands.

## Imports + library layout (v0.6-A)

v0.6-A introduces deterministic rule-module imports:

```sr
import lib.util

rule "Main" in underlying:
    when true:
        then annotate(note="ok")
```

See `docs/rule_library_layout.md` for the pack root rules, module naming, and cycle behavior.

## Packaging (v0.6-B)

Create a local bundle:

```bash
sigmadsl pack tests/fixtures/imports/pack_ok/main.sr --out pack_ok.zip --name pack_ok --version 0.1.0
```

Validate a bundle:

```bash
sigmadsl validate --pack pack_ok.zip
```

`validate --pack` performs pack integrity checks and then runs the same parse/import/type validation as `sigmadsl validate` on the embedded sources (guardrails remain in `sigmadsl lint`).

See `docs/rule_pack_model.md` for the artifact layout and manifest fields.

## Decision profiles + stable outputs (v1.0-A)

v1.0-A introduces explicit decision profiles and a stable decision output schema.

By default, the CLI runs in the `signal` profile. You can select a different profile explicitly:

```bash
sigmadsl validate path/to/rules.sr --profile intent
sigmadsl run --input bars.csv --rules path/to/rules.sr --profile risk
```

See `docs/decision_profiles.md` for the implemented allowlists and the stable decision schema.

## Risk constraints (v1.0-B)

v1.0-B adds a separate deterministic risk phase that can block prior decisions in a fail-closed way.

Runnable examples live under `examples/risk_rules/`.

```bash
sigmadsl run --profile signal --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/signal_always --risk-rules examples/risk_rules/packs/risk_block_close
```

See `docs/risk_constraints.md` for the implemented semantics.

## Reports (v1.0-C)

Sprint v1.0-C adds a small reporting surface that aggregates outcomes per rule / symbol / day from a decision JSONL stream:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr > decisions.jsonl
sigmadsl report --input decisions.jsonl
```

## Equity quickstart + FAQ

- `docs/equity_product_quickstart.md`
- `docs/faq.md`
