# SigmaDSL — High-level DSL v1.0

Status: Implemented (v1.0-A profile model + stable decision schema).  
Scope: **Sprint v1.0-A** (“Signal / Intent / Risk profiles”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (thesis backbone)
- `docs/high_level_dsl_v0.6.md`: v0.6 snapshot (imports + packaging)
- `docs/dsl_v1.0.md`: spec snapshot for v1.0 (copy-forward with profile + decision schema chapters concretized)

This document describes what is **new** at the **v1.0 boundary**, based on implemented behavior in the repo.

## What v1.0 adds (v1.0-A)

### 1) Explicit decision profiles

Profiles are now implemented as an explicit model and affect validation and outputs:

- `signal`: produces signal/annotation decisions
- `intent`: produces intent decisions (outputs only; no plan generation yet)
- `risk`: produces constraint decisions (outputs only; enforcement is later)

Currently, profile selection is done via CLI `--profile` (there is not yet an in-language profile header).

### 2) Stable decision schema

`sigmadsl run` / `sigmadsl replay` now emit a stable decision schema:

- envelope fields (`schema`, `schema_version`, `id`, `kind`, `profile`, `verb`, `trace_ref`, …)
- kinds: `signal` | `annotation` | `intent` | `constraint`
- deterministic trace linkage per decision via `trace_ref`

See `docs/decision_profiles.md` for the schema details.

### 3) Backward-compat mindset

Signal-profile outputs retain legacy top-level fields (e.g., `id`, `kind`, `rule_name`, `symbol`, `event_index`, `timestamp`)
while adding the v1.0 envelope fields.

## CLI behavior

- `sigmadsl validate <path> --profile {signal|intent|risk}`
- `sigmadsl lint <path> --profile {signal|intent|risk}`
- `sigmadsl run ... --profile {signal|intent|risk}`

`sigmadsl replay` and `sigmadsl diff` remain deterministic; run logs record the selected profile.

## Known limitations / deferred items

- no in-language profile declaration yet (CLI-only selection in v1.0-A)
- intent decisions are not converted into plans (later)
- risk constraints are not enforced against other outputs yet (v1.0-B)

