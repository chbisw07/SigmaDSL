# SigmaDSL — High-level DSL v0.4

Status: Implemented (event log + deterministic replay).  
Scope: **Sprint 0.4-A** (“Event log + replay”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.3.md`: v0.3 snapshot (deterministic evaluator + CSV runner + JSON decisions + basic explain)
- `docs/dsl_v0.4.md`: spec snapshot for v0.4 (copy-forward of spec with replay semantics concretized)

This document describes what is **new** at the **v0.4 boundary**, based on implemented behavior in the repo.

## What v0.4 adds (Sprint 0.4-A)

v0.4 introduces the first replayable workflow:

- a deterministic, versioned run log format capturing replayable snapshots
- `sigmadsl run --log-out ...` to write a replay log alongside decision outputs
- `sigmadsl replay --log ...` to reproduce the same decision outputs deterministically
- equivalence tests proving `run` output == `replay` output for the current equity/bar subset

## Replay model (v0.4-A)

Replay is **self-contained and fail-closed**:

- the log embeds:
  - rule file contents + hashes
  - normalized input events (bars + minimal flags)
  - CSV metadata (path/hash/columns) for provenance only
- replay recompiles rules from the embedded snapshot and re-evaluates events from the embedded snapshot
- replay does not depend on the current filesystem state of the original rule/CSV files

## CLI / user-visible behavior (v0.4-A)

Generate a run log:

```bash
sigmadsl run --input path/to/bars.csv --rules path/to/rules/ --log-out runlog.json
```

Replay a run log:

```bash
sigmadsl replay --log runlog.json
```

Replay output is the same decision JSONL format as `run` (or `--format json`).

## Guarantees (current scope)

- deterministic decisions output for the current single-symbol equity/bar runner
- replay output matches original run output exactly (same ordering, same JSONL lines)

## Known limitations / deferred items

- diff UX (`sigmadsl diff`) is deferred to v0.4-B
- multi-symbol evaluation and replay remain deferred
- trace persistence as a separate log/artifact is deferred (trace is re-computed during replay)
- indicators, imports/packaging, options/chain, planning/risk remain out of scope

## Version summary (what changed in v0.4)

- added versioned run log format (`sigmadsl.runlog` v0.4-a)
- added `sigmadsl replay` and run-log emission via `sigmadsl run --log-out ...`
- added replay equivalence tests

