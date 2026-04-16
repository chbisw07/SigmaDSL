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

