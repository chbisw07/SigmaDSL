# Option chain context (v1.2-A)

This example demonstrates **atomic option chain snapshots** evaluated in the `chain` context.

Scope (v1.2-A):
- chain quality / completeness predicates only (no chain analytics)
- deterministic “unknown” policy for incomplete chain snapshots

Scope (v1.2-B):
- derived chain metrics v1: PCR (OI/volume), OI change, IV skew-style metric
- deterministic rounding + Unknown behavior for missing/insufficient data

## Run

```bash
sigmadsl run \
  --context chain \
  --input examples/option_chain_context/data/chain_demo.csv \
  --rules examples/option_chain_context/chain_quality.sr
```

Expected output is recorded in:
- `examples/option_chain_context/expected/run_chain_demo.jsonl`

## Derived metrics demo (v1.2-B)

```bash
sigmadsl run \
  --context chain \
  --input examples/option_chain_context/data/chain_metrics.csv \
  --rules examples/option_chain_context/chain_metrics.sr
```

Expected output:
- `examples/option_chain_context/expected/run_chain_metrics.jsonl`

## What this example shows

- event 0: complete/fresh snapshot → `chain.quality_ok` emits `chain_ok`
- event 1: incomplete snapshot → `chain.has_unknowns` emits `chain_unknown`

## Worked examples (v1.2-C)

Runnable worked examples live under `examples/option_chain_context/worked_examples/`.

Each file is designed to be run with one of the small datasets under `examples/option_chain_context/data/`,
and the expected outputs live under `examples/option_chain_context/expected/worked_examples/`.

Example commands:

```bash
sigmadsl run --context chain --input examples/option_chain_context/data/chain_demo.csv --rules examples/option_chain_context/worked_examples/01_chain_quality_gate.sr
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/worked_examples/02_pcr_sentiment.sr
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/worked_examples/03_iv_skew_alert.sr
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/worked_examples/04_pcr_volume_high.sr
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/worked_examples/05_bearish_confirmed.sr
sigmadsl run --context chain --input examples/option_chain_context/data/chain_incomplete_only.csv --rules examples/option_chain_context/worked_examples/06_unknown_incomplete_chain.sr
```
