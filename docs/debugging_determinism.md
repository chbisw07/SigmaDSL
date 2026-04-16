# Debugging Determinism (v0.4)

This page describes the v0.4 workflow for reproducing and debugging rule outcomes deterministically.

## The core loop

1) Run deterministically and write a log:

```bash
sigmadsl run --input bars.csv --rules rules/ --log-out runlog.json
```

2) Replay from the log (should match the original run output exactly):

```bash
sigmadsl replay --log runlog.json
```

3) Diff two logs when behavior changes:

```bash
sigmadsl diff run_a.json run_b.json
```

4) Explain a specific decision (why it fired):

```bash
sigmadsl explain --decision-id D0003 --input bars.csv --rules rules/
```

5) Explain a rule at a specific event (why it didn’t fire):

```bash
sigmadsl explain --rule "EQ: Breakout" --event-index 0 --input bars.csv --rules rules/
```

## What “replay” guarantees in v0.4

- The run log is self-contained: it embeds rule text snapshots and normalized input events.
- `sigmadsl replay` recompiles from embedded snapshots and re-evaluates from embedded events.
- Replay output is deterministic and should match the original run output (tests enforce equivalence).

## What “diff” compares

`sigmadsl diff` compares **decision outputs**:

- it replays both logs deterministically, then
- compares the ordered decision JSONL stream exactly, and
- reports:
  - counts summary, and
  - the first divergence (index + decision lines).

In v0.4, `diff` does not attempt to diff traces (that is intentionally deferred).

## Timestamp / timezone behavior (v0.4)

v0.4 treats input timestamps as **opaque strings**:

- timestamps are preserved exactly in decisions, traces, and logs
- no timestamp parsing or timezone normalization exists yet
- outputs are invariant to the process timezone (`TZ`) (covered by tests)

If you change the timestamp string representation in inputs, it will be treated as a meaningful change.

## Common mismatch causes (v0.4)

- rule text changed (different snapshots lead to different decisions)
- CSV content changed (different bars/events)
- allowed built-in functions or verb signatures changed (type/lint/runtime differences)
- ordering changes (rule order or event order) — guarded by goldens and diff

