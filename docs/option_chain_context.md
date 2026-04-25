# Option chain context (v1.2-A / v1.2-B)

Sprint **v1.2-A** introduces a minimal, deterministic **option chain snapshot** input model and a runnable `chain` context.

Scope (v1.2-A):
- atomic chain snapshots (grouped and evaluated as one unit)
- strict CSV input (`sigmadsl run --context chain`)
- first-class quality predicates (`chain.is_fresh`, `chain.is_complete`, `chain.has_unknowns`, `chain.quality_ok`)
- deterministic **Unknown** policy for incomplete chain snapshots
- replayable run logs for chain runs (`--log-out` + `sigmadsl replay`)

Scope (v1.2-B):
- derived chain metrics v1 (PCR, OI change, skew-style metric)
- deterministic rounding for metrics (Decimal-backed)
- metric-level Unknown behavior for missing inputs / zero denominators / missing prior snapshot

Out of scope (later sprints):
- advanced chain analytics (max pain, skew surfaces by strike/tenor, OI concentration, etc.)
- `in chain:` access to per-contract arrays or general aggregations
- strategy generation / broker execution

## What a chain snapshot is

A chain snapshot is a point-in-time set of option contract rows for a single:
- `venue`
- `underlying`
- snapshot timestamp

In v1.2-A, the engine treats each snapshot timestamp group as an **atomic** evaluation event.

## CSV format (v1.2-A)

Run with:

```bash
sigmadsl run --context chain --input chain.csv --rules path/to/chain_rules.sr
```

Required columns:
- `snapshot_timestamp`
- `contract_id` (canonical `OPT:...` id)

Optional columns (parsed deterministically if present):
- quotes: `bid`, `ask`, `last`, `close`
- IV/greeks: `iv`, `delta`, `gamma`, `theta`, `vega`
- sizes: `open_interest` (or `oi`), `volume`
- explicit guards: `data_is_fresh`, `quality_flags` (comma-separated tokens)

Atomic grouping rule:
- rows are grouped by exact `snapshot_timestamp` string
- within one snapshot timestamp group, mixed `venue` or `underlying` is rejected (fail closed)
- duplicate `contract_id` within a group is rejected (fail closed)

## Quality predicates (first-class)

Chain rules can use the following deterministic predicates:

- `chain.is_fresh`: `true` when **all** contract rows are `data_is_fresh=true` and no row has `quality_flags`
- `chain.is_complete`: `true` when **all** contract rows are usable (fresh + required quote presence)
- `chain.has_unknowns`: `true` when the snapshot is not complete (`not chain.is_complete`)
- `chain.quality_ok`: `true` when complete **and** fresh (convenience predicate)

Timestamp identity fields:
- `chain.as_of` and `chain.time` are aliases for the snapshot timestamp string carried by the event.

## Derived chain metrics v1 (v1.2-B)

In v1.2-B, the `chain` context exposes a small, explicit derived-metrics surface as **read-only fields**:

- `chain.pcr_oi: Decimal`
  - put open interest / call open interest
- `chain.pcr_volume: Decimal`
  - put volume / call volume
- `chain.oi_change: Quantity`
  - net chain open-interest change vs the immediately previous snapshot
- `chain.oi_change_puts: Quantity`
- `chain.oi_change_calls: Quantity`
- `chain.iv_skew: Percent`
  - mean(put_iv) - mean(call_iv) (skew-style; not strike-matched yet)

### Metric guard policy (fail closed)

All derived metrics are **Unknown** unless the snapshot is “quality OK”:

- `chain.is_complete=true`
- `chain.is_fresh=true`
- no `quality_flags`

In addition:
- PCR metrics require the required fields on **all** contracts in the snapshot.
- PCR denominators must be `> 0` (zero denominator → Unknown).
- OI change metrics require a prior snapshot and require identical contract-id sets between prev/current (fail closed).

### Deterministic rounding

- `chain.pcr_oi` and `chain.pcr_volume` are quantized to **4 dp** (e.g., `1.5000`).
- `chain.iv_skew` is quantized to **6 dp** (matching the IV input quantization).
- OI change metrics are integer `Decimal` values (no fractional).

## Deterministic Unknown policy (incomplete chain snapshots)

When `chain.has_unknowns` is `true`, v1.2-A applies a conservative unknown policy:

1) A predicate that does **not** reference any chain quality fields is recorded as **Unknown** and does not match.
2) `else` branches are disabled (fail closed) while `chain.has_unknowns` is `true`.

This prevents rules like:

```sr
rule "Bad" in chain:
    when true:
        then emit_signal(kind="X")
```

from emitting decisions on incomplete chain snapshots.

Metric-level Unknowns:
- even on complete snapshots, a derived metric can still be Unknown (missing required fields / zero denom / missing prior snapshot).
- Unknown predicate outcomes do not match and are surfaced as `Unknown` in `sigmadsl explain`.

You can inspect this in trace output:

```bash
sigmadsl explain --context chain --rule "Bad" --event-index 0 --input chain.csv --rules rules.sr
```

## Example pack

Runnable examples live in:
- `examples/option_chain_context/`

Run:

```bash
sigmadsl run --context chain --input examples/option_chain_context/data/chain_demo.csv --rules examples/option_chain_context/chain_quality.sr
```

Derived metrics demo:

```bash
sigmadsl run --context chain --input examples/option_chain_context/data/chain_metrics.csv --rules examples/option_chain_context/chain_metrics.sr
```

## Replay (v0.4-A + v1.2-A)

Chain runs can be logged and replayed deterministically:

```bash
sigmadsl run --context chain --input chain.csv --rules rules.sr --log-out runlog.json
sigmadsl replay --log runlog.json
```
