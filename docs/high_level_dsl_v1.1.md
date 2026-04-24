# SigmaDSL — High-level DSL v1.1

Status: Implemented (v1.1-A option contract model + types).  
Scope: **Sprint v1.1-A** (“Option instrument model + types”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/high_level_dsl_v1.0.md`: stable equity product snapshot (profiles + risk + report)
- `docs/DSL_v0.md`: foundational design/spec (thesis backbone)
- `docs/dsl_v1.1.md`: spec snapshot for v1.1 (copy-forward with option contract chapters concretized)

## What v1.1 adds (v1.1-A)

### 1) Option contract identity model

v1.1-A introduces an explicit option contract identity model:

- venue
- underlying
- expiry (date)
- strike
- right (CALL/PUT)
- lot size

### 2) Canonical option contract ids

Option contracts are represented with a deterministic, broker-agnostic canonical id:

```
OPT:<VENUE>:<UNDERLYING>:<EXPIRY>:<STRIKE>:<RIGHT>:<LOT>
```

See `docs/options_contract_context.md` for the full validation rules.

### 3) Option snapshot input model (atomic)

v1.1-A defines a minimal atomic snapshot shape (quotes + optional greeks inputs) with explicit data quality fields:

- `data_is_fresh`
- `quality_flags`

This lays the groundwork for deterministic option-context execution in v1.1-B.

### 4) Typed validation for `option` context rules

`sigmadsl validate` now supports `in option:` rules for type checking using an explicit option field environment.

Runner support for option snapshot inputs is intentionally deferred.

## Known limitations / deferred items

- no option CSV runner yet (v1.1-B)
- no option context binding / selection helpers yet (v1.1-B / v1.1-C)
- no chain context (v1.2+)

