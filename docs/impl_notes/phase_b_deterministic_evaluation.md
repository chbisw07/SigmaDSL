# Phase B — Deterministic Evaluation + Explainability (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md` (project plan / roadmap).  
This document accumulates engineering notes for Phase B sprints (v0.3–v0.4).

---

## Sprint 0.3-A — Deterministic evaluator + trace

### Sprint goal

Implement the first deterministic runtime slice for equity/bar-based rules:

- evaluate `underlying` rules against an in-memory bar/event series
- emit structured decisions (signals / annotations only in this sprint)
- produce a stable explainability trace showing rule evaluation + predicate outcomes
- prove determinism with goldens on small bar series

### What was implemented

- **Runtime input model** (`src/sigmadsl/runtime_models.py`):
  - `Bar` (OHLCV + `timestamp` as an opaque string identity in v0.3-A)
  - `UnderlyingEvent` (symbol + event index + bar + minimal flags)
- **Decision output model** (`src/sigmadsl/decisions.py`):
  - `SignalDecision` via `emit_signal(...)`
  - `AnnotationDecision` via `annotate(...)`
  - stable decision IDs (`D0001`, `D0002`, …) in emission order
- **Trace model** (`src/sigmadsl/trace.py`):
  - `RunTrace` → `EventTrace` → `RuleTrace`
  - captures:
    - each branch predicate result (`when` / `elif` / `else`)
    - selected branch (or none)
    - actions invoked (verb + args) + emitted decision IDs
- **Evaluator** (`src/sigmadsl/evaluator.py`):
  - `compile_source_file(...)` turns parsed AST rules into `CompiledRule` objects with stable ordering metadata
  - `evaluate_underlying(...)` runs a deterministic evaluation pass over events, producing:
    - `decisions` (ordered list)
    - `trace` (ordered by event then rule)

### Determinism + ordering policy (v0.3-A)

- **Event order**: the evaluator processes events in the list order; `UnderlyingEvent.index` must match the list position (0..N-1).
- **Rule order** (deterministic tie-breakers):
  1. file path (lexicographic string)
  2. source order within file (rule index)
  3. rule name (lexicographic)
- **Branch order**: evaluated in source order (`when`, then `elif`…, then optional `else`).
- **Action order**: `then` lines are emitted in source order within the selected branch.
- **Numeric stability**: runtime uses `Decimal`; trace/decision JSON normalizes decimals to non-scientific strings for goldens.

### Supported runtime semantics (deliberately small)

This sprint implements only what is needed to evaluate the current minimal DSL subset:

- literals: bool, string, int/decimal, percent (`0.2%` becomes `0.002`)
- names + dotted fields: `bar.close`, `data.is_fresh`, `session.is_regular`, `underlying.return_5m` (PROVISIONAL)
- boolean ops: `and`, `or`, `not` (short-circuit)
- comparisons: numeric comparisons; string supports `==` / `!=` only
- whitelisted pure functions (same as typing/lint):
  - `abs(x)`
  - `highest(series, n)`, `lowest(series, n)`
  - `prior_high(n)`, `prior_low(n)`
- verbs supported at runtime:
  - `emit_signal(kind=..., reason?=..., strength?=...)`
  - `annotate(note=...)`

Anything outside the supported runtime subset raises an `EvalError` (the expectation is that
`validate`/`lint` prevent most unsupported constructs from reaching the evaluator).

### Tests + golden strategy

- Bar-series fixtures: `tests/fixtures/eval/*.json`
- Rule fixtures: `tests/fixtures/eval/*.sr`
- Golden evaluator outputs: `tests/golden/eval_*.json`
- Determinism checks:
  - golden outputs verify stable trace shape and ordering
  - repeated-run tests assert `evaluate_underlying(...)` is stable

### Commands to run

Run the full test suite:

```bash
pytest
```

Run only the v0.3-A evaluator tests:

```bash
pytest -k evaluator
```

### Known limitations (intentionally deferred)

Not implemented in Sprint 0.3-A (by design):

- `sigmadsl run` CLI (CSV runner + JSON output is Sprint 0.3-B)
- replay/diff and parity harness (v0.4)
- indicators registry and window semantics hardening (v0.5)
- imports/packaging (v0.6)
- option/chain contexts, intent/plan/risk semantics (v1.x / v2.0)
- missing/unknown three-valued logic (still TBD in `docs/DSL_v0.md`)

---

## Sprint 0.3-B — CLI run + JSON output

### Sprint goal

Turn the v0.3-A evaluator into a user-runnable product slice:

- add `sigmadsl run --input bars.csv --rules path/` emitting deterministic JSON decision outputs
- add `sigmadsl explain --decision-id ...` to inspect why a decision fired (basic)
- add end-to-end fixtures and CLI goldens (CSV → expected JSON/trace output)

### What was implemented

- **CSV loader (strict, sprint-scoped)**: `src/sigmadsl/csv_input.py`
  - required columns: `symbol,timestamp,open,high,low,close,volume`
  - optional columns: `underlying_return_5m,data_is_fresh,session_is_regular`
  - v0.3-B supports **single-symbol series only** (fails deterministically otherwise)
- **Runner pipeline**: `src/sigmadsl/runner.py`
  - loads rule files (`*.sr`) from a file or directory path (sorted)
  - runs parse → typecheck → lint before evaluation (fail-closed)
  - runs v0.3-A evaluator and returns decisions + trace
  - provides stable JSONL serialization for decisions
  - provides a basic explain formatter for one decision
- **CLI commands**: `src/sigmadsl/cli.py`
  - `sigmadsl run --input ... --rules ... [--format jsonl|json]`
  - `sigmadsl explain --decision-id ... --input ... --rules ...`

### Output format choices (v0.3-B)

- Default `run` output is **JSONL** (one decision per line), suitable for piping:
  - deterministic decision ordering (event → rule → action)
  - stable key ordering in each JSON object (`sort_keys=True`)
- `--format json` emits a single JSON array of decisions (decisions-only; trace is internal for now)

### Tests + fixtures

- CSV fixtures: `tests/fixtures/run/*.csv`
- End-to-end CLI goldens:
  - `tests/golden/run_*.jsonl`
  - `tests/golden/explain_d0003.txt`
- Tests:
  - `tests/test_cli_run.py`
  - `tests/test_cli_explain.py`

### Commands to run

Run the full test suite:

```bash
pytest
```

Manual demo (stdout):

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
sigmadsl explain --decision-id D0003 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

### Known limitations (intentionally deferred)

- multi-symbol CSV evaluation (per-symbol histories + deterministic merge) is deferred
- trace export to a separate file/log is deferred (replay logging is v0.4)
- replay/diff, indicators, imports/packaging, options/chain, planning/risk remain out of scope

---

## Sprint 0.4-A — Event log + replay

### Sprint goal

Make v0.3 runs replayable and reproducible:

- define a deterministic, versioned event log format capturing the minimal replayable snapshot
- integrate run logging into `sigmadsl run --log-out ...`
- implement `sigmadsl replay --log ...` that reproduces the same outputs deterministically
- add replay equivalence tests proving run output == replay output

### Event log design (v0.4-A)

Log format: a single JSON file (self-contained snapshot).

Key design choice: **embed canonical snapshots** instead of relying on external files at replay time:

- embedded rule file texts + sha256 (for integrity)
- embedded normalized input events (bars/fields)
- CSV metadata (path, sha256, columns, row_count) for provenance only

This makes replay robust even if the original `.sr` files or CSV change after the run.

### What was implemented

- **Run log schema + loader**: `src/sigmadsl/runlog.py`
  - schema: `sigmadsl.runlog`
  - schema_version: `0.4-a`
- **Runner integration**: `src/sigmadsl/runner.py`
  - `run_underlying_from_csv_with_log(..., log_out=...)` writes a replayable log on success
  - `replay_from_log(log_path=...)` recompiles rules from embedded snapshots and re-evaluates
- **CLI command**: `src/sigmadsl/cli.py`
  - `sigmadsl run ... --log-out runlog.json`
  - `sigmadsl replay --log runlog.json`
- **Tests**: `tests/test_cli_replay.py`
  - run + log-out, then replay, assert outputs match exactly
  - reject unsupported log schema deterministically

### Commands to run

Run + log:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr --log-out runlog.json
```

Replay:

```bash
sigmadsl replay --log runlog.json
```

Test suite:

```bash
pytest
```

### Known limitations (intentionally deferred)

- diff/analyzer UX (`sigmadsl diff`) is deferred to a later sprint (v0.4-B)
- replay currently re-emits decisions only (trace is re-computed but not persisted separately yet)
- multi-symbol replay is still deferred (matches v0.3 runner scope)
