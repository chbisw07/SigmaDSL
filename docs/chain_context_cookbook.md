# Chain context cookbook (v1.2)

This cookbook shows how to author **chain snapshot** rules using SigmaDSL’s `chain` context.

Scope (implemented in v1.2-A/B):
- atomic chain snapshots (`sigmadsl run --context chain`)
- quality predicates:
  - `chain.is_fresh`, `chain.is_complete`, `chain.has_unknowns`, `chain.quality_ok`
- derived metrics v1:
  - `chain.pcr_oi`, `chain.pcr_volume`
  - `chain.oi_change`, `chain.oi_change_puts`, `chain.oi_change_calls`
  - `chain.iv_skew`
- deterministic **Unknown** behavior (fail-closed)

Out of scope (deferred):
- max pain / GEX / probability models
- strike/tenor skew surfaces and smile analytics
- per-contract iteration/aggregation surfaces
- strategy generation, broker execution

## 1) What `in chain:` means

- A rule is evaluated against an **atomic option chain snapshot** event.
- The DSL exposes a small, explicit set of `chain.*` fields and metrics.
- Evaluation is deterministic and replayable; missing/insufficient data becomes **Unknown**, not `0`.

## 2) Atomic chain snapshots

Chain CSV rows are grouped into a snapshot by exact `snapshot_timestamp` string.
All contracts in a snapshot are evaluated as one unit.

See `docs/option_chain_context.md` for the full CSV format and atomic grouping rules.

## 3) Quality predicates (first-class)

Use these to guard authoring:

- `chain.is_fresh`: all rows have `data_is_fresh=true` and no `quality_flags`
- `chain.is_complete`: all rows are usable (fresh + required quote presence)
- `chain.has_unknowns`: `true` when the snapshot is not complete
- `chain.quality_ok`: convenience: complete + fresh + no flags

### Example: quality gate

```sr
rule "CHAIN: Quality Gate" in chain:
    when chain.quality_ok:
        then emit_signal(kind="CHAIN_OK", reason="quality_ok")
```

Runnable: `examples/option_chain_context/worked_examples/01_chain_quality_gate.sr`.

## 4) PCR metrics

### `chain.pcr_oi`

Definition (v1.2-B):
- put open interest sum / call open interest sum
- requires `open_interest` on all contracts
- call OI denominator must be `> 0`
- quantized to 4 dp (half-up)

### `chain.pcr_volume`

Definition (v1.2-B):
- put volume sum / call volume sum
- requires `volume` on all contracts
- call volume denominator must be `> 0`
- quantized to 4 dp (half-up)

### Example: PCR-based sentiment (with OI-change confirmation)

```sr
rule "CHAIN: Put-Call OI Imbalance" in chain:
    when chain.is_fresh and chain.pcr_oi > 1.3 and chain.oi_change_puts > chain.oi_change_calls:
        then emit_signal(kind="BEARISH_SENTIMENT", reason="pcr_oi_high_put_oi_rising")
```

Runnable: `examples/option_chain_context/worked_examples/02_pcr_sentiment.sr`.

## 5) OI change metrics

v1.2-B exposes net change vs the immediately previous snapshot:

- `chain.oi_change` (net across all contracts)
- `chain.oi_change_puts`
- `chain.oi_change_calls`

Fail-closed requirements:
- there must be a prior snapshot
- the contract-id set must match exactly between prior/current
- open interest must be present on all rows

If any requirement fails, the metric is **Unknown**.

## 6) IV skew metric (v1 surface)

`chain.iv_skew` is a narrow skew-style metric:

- `mean(put_iv) - mean(call_iv)`
- requires `iv` on all contracts
- quantized to 6 dp (half-up)

Example:

```sr
rule "CHAIN: IV Skew Alert" in chain:
    when chain.quality_ok and abs(chain.iv_skew) > 3%:
        then emit_signal(kind="SKEW_ALERT", reason="iv_skew_abs_gt_3pct")
```

Runnable: `examples/option_chain_context/worked_examples/03_iv_skew_alert.sr`.

## 7) How to interpret `Unknown`

Unknown is intentionally conservative:
- metrics become Unknown if required data is missing or insufficient (including “no prior snapshot” for OI change)
- Unknown predicate outcomes do not match (no decision is emitted)
- `else` branches are disabled when `chain.has_unknowns=true`

To see Unknown in action:

```bash
sigmadsl explain \
  --context chain \
  --rule "CHAIN: Put-Call OI Imbalance" \
  --event-index 0 \
  --input examples/option_chain_context/data/chain_metrics.csv \
  --rules examples/option_chain_context/worked_examples/02_pcr_sentiment.sr
```

## 8) Worked examples index

All runnable worked examples live under:
- `examples/option_chain_context/worked_examples/`

Expected outputs live under:
- `examples/option_chain_context/expected/worked_examples/`

Run one example and compare output:

```bash
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/worked_examples/02_pcr_sentiment.sr > out.jsonl
diff -u examples/option_chain_context/expected/worked_examples/02_pcr_sentiment.jsonl out.jsonl
```

