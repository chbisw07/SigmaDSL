# Option chain context (v1.2-A)

This example demonstrates **atomic option chain snapshots** evaluated in the `chain` context.

Scope (v1.2-A):
- chain quality / completeness predicates only (no chain analytics)
- deterministic “unknown” policy for incomplete chain snapshots

## Run

```bash
sigmadsl run \
  --context chain \
  --input examples/option_chain_context/data/chain_demo.csv \
  --rules examples/option_chain_context/chain_quality.sr
```

Expected output is recorded in:
- `examples/option_chain_context/expected/run_chain_demo.jsonl`

## What this example shows

- event 0: complete/fresh snapshot → `chain.quality_ok` emits `chain_ok`
- event 1: incomplete snapshot → `chain.has_unknowns` emits `chain_unknown`

