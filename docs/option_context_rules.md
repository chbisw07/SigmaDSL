# Option context rules (v1.1-B)

Sprint v1.1-B adds **runtime binding** for rules authored with `in option:`.

This means `sigmadsl run` can evaluate a rule pack against an **atomic option snapshot CSV** for a single option contract.

## What `in option:` means

- The rule is evaluated in the **option contract snapshot** context.
- Field access is restricted to the explicit option environment (no Python, no dynamic lookups).
- The runner binds the context from input snapshots; there is no fuzzy matching.

## Running option rules

Validate a rule pack:

```bash
sigmadsl validate path/to/option_rules.sr
```

Run on an option snapshot CSV:

```bash
sigmadsl run --context option --input options.csv --rules path/to/option_rules.sr
```

If the CSV contains multiple distinct `contract_id` values, choose one deterministically:

```bash
sigmadsl run \
  --context option \
  --contract-id OPT:NSE:TCS:2026-01-29:100:CALL:150 \
  --input options.csv \
  --rules path/to/option_rules.sr
```

## CSV format

The full contract id format is documented in `docs/options_contract_context.md`.

At minimum, the CSV must include:
- `contract_id`
- `timestamp`

Quote and IV/greeks columns are optional, but rule evaluation will fail closed if a snapshot is unusable (see below).

## Data quality (fail-closed)

For determinism and safety, the runner rejects unusable snapshots:
- `data_is_fresh=false`
- missing quote data (no `last`, no `close`, and not both `bid`+`ask`)
- any non-empty `quality_flags`

## Example pack

Runnable examples live in `examples/option_context_rules/`:

```bash
sigmadsl run \
  --context option \
  --input examples/option_context_rules/data/options_basic.csv \
  --rules examples/option_context_rules/option_signals.sr
```

## What is intentionally not implemented yet

- option chain context (`in chain:`) and chain-derived metrics (v1.2+)
- automatic contract selection helpers (ATM/weekly selection, etc.)
- broker execution or planning/routing semantics

