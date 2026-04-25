# Option chain context (v1.2-A)

Sprint **v1.2-A** introduces a minimal, deterministic **option chain snapshot** input model and a runnable `chain` context.

Scope (v1.2-A):
- atomic chain snapshots (grouped and evaluated as one unit)
- strict CSV input (`sigmadsl run --context chain`)
- first-class quality predicates (`chain.is_fresh`, `chain.is_complete`, `chain.has_unknowns`, `chain.quality_ok`)
- deterministic **Unknown** policy for incomplete chain snapshots
- replayable run logs for chain runs (`--log-out` + `sigmadsl replay`)

Out of scope (later sprints):
- chain-derived analytics (PCR/max pain/skew/OI concentration/etc.)
- `in chain:` access to per-contract arrays or derived metrics
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
- sizes: `open_interest`, `volume`
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

## Replay (v0.4-A + v1.2-A)

Chain runs can be logged and replayed deterministically:

```bash
sigmadsl run --context chain --input chain.csv --rules rules.sr --log-out runlog.json
sigmadsl replay --log runlog.json
```

