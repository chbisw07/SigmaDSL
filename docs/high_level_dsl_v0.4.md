# SigmaDSL — High-level DSL v0.4

Status: Implemented (replay + diff + explain UX).  
Scope: **Sprint 0.4-A** (“Event log + replay”) + **Sprint 0.4-B** (“Explain UX + golden suite”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.3.md`: v0.3 snapshot (deterministic evaluator + CSV runner + JSON decisions + basic explain)
- `docs/dsl_v0.4.md`: spec snapshot for v0.4 (copy-forward of spec with replay semantics concretized)

This document describes what is **new** at the **v0.4 boundary**, based on implemented behavior in the repo.

## What v0.4 adds (Sprints 0.4-A / 0.4-B)

v0.4 introduces the first replayable workflow:

- a deterministic, versioned run log format capturing replayable snapshots
- `sigmadsl run --log-out ...` to write a replay log alongside decision outputs
- `sigmadsl replay --log ...` to reproduce the same decision outputs deterministically
- equivalence tests proving `run` output == `replay` output for the current equity/bar subset

Sprint 0.4-B adds the first “debugging determinism” workflow:

- improved `sigmadsl explain` output (why fired / why not fired)
- `sigmadsl diff` to compare two run logs deterministically (counts + first divergence)
- stronger regression protection via goldens around explain/diff
- explicit timestamp/timezone invariants tested and documented

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

## Explain + diff (v0.4-B)

Explain (decision):

```bash
sigmadsl explain --decision-id D0003 --input path/to/bars.csv --rules path/to/rules/
```

Explain (rule at event):

```bash
sigmadsl explain --rule "EQ: Breakout" --event-index 0 --input path/to/bars.csv --rules path/to/rules/
```

Diff two run logs:

```bash
sigmadsl diff run_a.json run_b.json
```

Exit codes:
- `0` if equal
- `1` if different
- `2` on errors (malformed/unsupported logs)

## Timestamp/timezone behavior (v0.4)

v0.4 treats timestamps as **opaque strings**:

- they are preserved exactly in decision output, trace, and logs
- no timezone normalization/parsing exists yet
- determinism relies on stable input strings (tests enforce invariance to the process `TZ`)

## Guarantees (current scope)

- deterministic decisions output for the current single-symbol equity/bar runner
- replay output matches original run output exactly (same ordering, same JSONL lines)

## Known limitations / deferred items

- multi-symbol evaluation and replay remain deferred
- trace persistence as a separate log/artifact is deferred (trace is re-computed during replay)
- indicators, imports/packaging, options/chain, planning/risk remain out of scope

## Version summary (what changed in v0.4)

- added versioned run log format (`sigmadsl.runlog` v0.4-a)
- added `sigmadsl replay` and run-log emission via `sigmadsl run --log-out ...`
- added replay equivalence tests
- improved `sigmadsl explain` and added `sigmadsl diff`
