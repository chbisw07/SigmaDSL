# Options contract context (v1.1-A / v1.1-B)

This page describes the **implemented** option contract modeling foundations introduced in **Sprint v1.1-A**,
and the **runtime option context binding** introduced in **Sprint v1.1-B**.

Scope (v1.1-A):
- option contract identity model
- canonical (broker-agnostic) option identifiers
- deterministic parsing/validation (expiry/strike/right/lot)
- atomic option snapshot input model (quotes + optional greeks)
- explicit freshness/quality guard fields (no inferred staleness yet)

Scope (v1.1-B):
- runtime binding for rules authored with `in option:`
- strict option snapshot CSV input support in `sigmadsl run --context option`
- deterministic context selection (`--contract-id` if needed)
- fail-closed snapshot usability checks (`data_is_fresh`, quote presence, and `quality_flags`)

Scope (v1.1-C):
- deterministic selection helpers over explicit snapshot inputs:
  - ATM selection
  - nearest OTM selection
  - delta-based selection (when delta is present)

Out of scope (later sprints):
- option chain modeling / chain snapshots (v1.2+)

## Canonical option contract id (implemented)

SigmaDSL uses a deterministic, broker-agnostic identifier for fixtures and run logs.

Format:

```
OPT:<VENUE>:<UNDERLYING>:<EXPIRY>:<STRIKE>:<RIGHT>:<LOT>
```

Example:

```
OPT:NSE:TCS:2026-01-29:100:CALL:150
```

Rules:
- `VENUE`: `[A-Z0-9._-]{1,16}` (example: `NSE`)
- `UNDERLYING`: `[A-Z0-9._-]{1,32}` (example: `TCS`, `NIFTY`)
- `EXPIRY`: strict ISO date `YYYY-MM-DD` (no guessing)
- `STRIKE`: decimal with **at most 2** fractional digits (no fuzzy rounding)
- `RIGHT`: `CALL` or `PUT` (parser also accepts `C/P` and `CE/PE`, normalized to `CALL/PUT`)
- `LOT`: integer `> 0`

Strike normalization:
- strikes are parsed as `Decimal` and quantized to `0.01`
- canonical formatting uses a non-scientific form with trailing zeros removed (e.g. `100.00` → `100`)

## Option snapshot inputs (implemented model)

v1.1-A introduces an atomic snapshot model for a single option contract.

Fields (current model):
- `timestamp` (string; carried through as an identity in v1.1-A)
- `contract_id` (canonical id above)
- quote fields (optional): `bid`, `ask`, `last`
- optional greeks/IV inputs: `iv`, `delta`, `gamma`, `theta`, `vega`
- optional sizes: `open_interest`, `volume`
- explicit guards:
  - `data_is_fresh: bool`
  - `quality_flags: list[str]`

Numeric policy:
- all numeric values are parsed as `Decimal` (no float)
- IV is represented as a **ratio** in `[0,1]` when provided (consistent with DSL `Percent` literals being ratios)
- greeks are quantized to fixed precision for reproducibility in tests

## Staleness / quality guards (v1.1-A boundary)

In v1.1-A, staleness is not inferred from timestamps yet.

Instead:
- data sources must provide explicit `data_is_fresh`
- rule authors can guard with `data.is_fresh` once `option` context execution is delivered (v1.1-B)

This keeps determinism explicit and avoids environment-dependent time logic.

## CLI status (v1.1-A)

v1.1-A enabled **typed validation** of `option` context rule files.

```bash
sigmadsl validate tests/fixtures/options/option_ok.sr
```

## Running `in option:` rules on snapshot CSV (v1.1-B)

Sprint v1.1-B adds a strict, deterministic option snapshot runner:

```bash
sigmadsl run --context option --input options.csv --rules path/to/option_rules.sr
```

If the input CSV contains multiple distinct `contract_id` values, you must select one explicitly:

```bash
sigmadsl run \
  --context option \
  --contract-id OPT:NSE:TCS:2026-01-29:100:CALL:150 \
  --input options.csv \
  --rules path/to/option_rules.sr
```

### CSV columns (v1.1-B)

Required:
- `contract_id` (canonical id)
- `timestamp`

Optional (if present, parsed deterministically):
- identity cross-check: `venue`, `underlying`, `expiry`, `strike`, `right`, `lot`
- quotes: `bid`, `ask`, `last`, `close`
- IV/greeks: `iv`, `delta`, `gamma`, `theta`, `vega`
- sizes: `open_interest`, `volume`
- selection helpers: `underlying_price` (required for ATM/OTM selection)
- guards: `data_is_fresh`, `quality_flags`
- linkage: `underlying_return_5m`, `session_is_regular`

### Snapshot usability (v1.1-B)

The runner fails closed if any selected-row snapshot is unusable:
- `data_is_fresh=false`
- missing quote (no `last`, no `close`, and not both `bid`+`ask`)
- any non-empty `quality_flags`

This keeps execution deterministic and avoids silently producing decisions from explicitly flagged bad data.

## Selection helpers (v1.1-C)

v1.1-C adds deterministic selection helpers for multi-contract snapshot inputs.

These helpers select a **single contract stream** before evaluation (still atomic option context):

- `--select atm` (requires `--right CALL|PUT` and `underlying_price`)
- `--select otm` (requires `--right CALL|PUT` and `underlying_price`; nearest is `--otm-rank 1`)
- `--select delta` (requires `--right CALL|PUT` and `--target-delta`)

Optional filters:
- `--expiry YYYY-MM-DD` (restrict candidates to a specific expiry)

Selection timestamp rule (deterministic):
- selection is based on the **earliest timestamp** present in the CSV (lexicographic min)
- candidate rows are the **usable** snapshot rows at that timestamp (one row per contract id)

Tie-breakers (deterministic):
1) primary distance metric (ATM strike distance / OTM distance / delta distance)
2) earlier expiry
3) right order (CALL before PUT)
4) canonical contract id lexical order

Examples: see `examples/options_contract_rules/`.
