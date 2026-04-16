# SigmaDSL — High-level DSL v0.3

Status: Implemented (deterministic evaluator + trace).  
Scope: **Sprint 0.3-A** (“Deterministic evaluator + trace”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.2.md`: v0.2 snapshot (typed authoring + lint guardrails)

This document describes what is **new** at the **v0.3 boundary**, based on implemented behavior in the repo.

## What v0.3 adds (Sprint 0.3-A)

v0.3 introduces the first executable slice of SigmaDSL:

- a deterministic evaluator for a minimal `underlying` (equity) bar/event model
- deterministic decision outputs (signals + annotations only in v0.3-A)
- a stable explainability trace that records:
  - rule evaluation per event
  - branch predicate outcomes
  - which branch fired
  - what actions were emitted (verb + args) and which decision IDs were produced

## Runtime scope (v0.3-A)

### Supported context

- `underlying` only (equity/bar-based evaluation)

### Runtime input model

Minimal v0.3-A runtime event includes:

- `symbol`
- `index` (0..N-1)
- `bar` (OHLCV + `timestamp`)
- minimal flags:
  - `data.is_fresh`
  - `session.is_regular`
- provisional example field:
  - `underlying.return_5m`

### Expression evaluation (runtime)

v0.3-A runtime supports a conservative subset:

- literals: bool, string, numbers, percent literals (`0.2%` → `0.002`)
- names + dotted fields: `bar.close`, `data.is_fresh`, `session.is_regular`, `underlying.return_5m`
- boolean ops: `and`, `or`, `not`
- comparisons: numeric comparisons; string supports `==` / `!=` only
- pure whitelisted function calls:
  - `abs(x)`
  - `highest(series, n)`, `lowest(series, n)`
  - `prior_high(n)`, `prior_low(n)`

### Verbs / decision outputs (runtime)

Only a minimal “signal profile” output set is supported in v0.3-A:

- `emit_signal(kind=..., reason?=..., strength?=...)` → emits a `SignalDecision`
- `annotate(note=...)` → emits an `AnnotationDecision`

No broker execution or execution planning exists (still strictly “plan, don’t execute”).

## Determinism policy (v0.3-A)

Determinism is enforced via explicit ordering:

- events are evaluated in list order
- rules are evaluated in a stable sort order:
  1. file path (lexicographic)
  2. source order within file
  3. rule name
- branches and `then` lines are evaluated in source order
- decision IDs are assigned sequentially in emission order (`D0001`, `D0002`, …)

All trace/decision outputs are stable and suitable for golden tests.

## CLI / user-visible behavior (v0.3-A)

`sigmadsl validate` and `sigmadsl lint` continue to work as in v0.2.

Sprint 0.3-A does **not** ship a public `sigmadsl run` CLI yet (that is Sprint 0.3-B).
Instead, v0.3-A is verified via evaluator fixtures and golden tests in the repository.

## Guardrails remain in effect

- Python-shaped, not Python
- deterministic execution only (no IO/network/time access inside evaluation)
- no loops/functions/assignments/imports in authoring
- no broker execution inside the DSL boundary

## Known limitations / deferred items

- CSV runner and user-facing `sigmadsl run` command (Sprint 0.3-B)
- replay/diff and parity harness (v0.4)
- indicators (v0.5), imports/packaging (v0.6)
- options/chain contexts and intent/plan/risk (v1.x / v2.0)

## Version summary (what changed in v0.3)

- Added minimal equity/bar runtime model + deterministic evaluator
- Added stable trace records with predicate outcomes and emitted decisions
- Added fixture/golden test coverage proving deterministic behavior

