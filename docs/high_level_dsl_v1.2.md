# SigmaDSL — High-level DSL v1.2

Status: Implemented (Sprint v1.2-A chain snapshot semantics).  
Scope: **Sprint v1.2-A** (“Chain schema + snapshot semantics”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/high_level_dsl_v1.1.md`: option contract context + option snapshot runner + selection helpers
- `docs/dsl_v1.2.md`: spec snapshot for v1.2 (copy-forward with chain snapshot sections concretized)
- `docs/DSL_v0.md`: foundational design/spec (thesis backbone)

## What v1.2 adds (v1.2-A)

### 1) Atomic chain snapshot inputs

v1.2-A introduces an explicit **chain snapshot** input model:

- rows grouped by a single `snapshot_timestamp`
- a snapshot is evaluated as one atomic event
- strict, deterministic CSV parsing (no fuzzy matching)

### 2) Runnable `chain` context

Rules authored with `in chain:` are now runnable via:

```bash
sigmadsl run --context chain --input chain.csv --rules path/to/chain_rules.sr
```

Scope (v1.2-A): quality predicates only (no chain analytics).

### 3) First-class quality predicates

The `chain` context exposes conservative quality predicates for authors:

- `chain.is_fresh`
- `chain.is_complete`
- `chain.has_unknowns`
- `chain.quality_ok`

Timestamp identity fields:
- `chain.as_of` (with `chain.time` as an alias)

### 4) Deterministic Unknown policy

When a chain snapshot is incomplete (`chain.has_unknowns=true`), v1.2-A applies a fail-closed policy:

- predicates that don’t reference chain quality fields evaluate as **Unknown** (and do not match)
- `else` branches are disabled while unknowns are present

### 5) Replay support

Chain runs can be recorded and replayed deterministically using the existing run log mechanism:

```bash
sigmadsl run --context chain --input chain.csv --rules rules.sr --log-out runlog.json
sigmadsl replay --log runlog.json
```

## Examples and docs

- user doc: `docs/option_chain_context.md`
- implementation notes: `docs/impl_notes/phase_f_options_contract_context.md`
- runnable pack: `examples/option_chain_context/`

## Deferred (not in v1.2-A)

- chain-derived metrics/analytics (PCR/max pain/skew/etc.)
- chain iteration/aggregation over contracts
- strategy generation, broker execution, planning/routing

