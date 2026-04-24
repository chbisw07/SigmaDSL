# Options contract context (v1.1-A)

This page describes the **implemented** option contract modeling foundations introduced in **Sprint v1.1-A**.

Scope (v1.1-A):
- option contract identity model
- canonical (broker-agnostic) option identifiers
- deterministic parsing/validation (expiry/strike/right/lot)
- atomic option snapshot input model (quotes + optional greeks)
- explicit freshness/quality guard fields (no inferred staleness yet)

Out of scope (later sprints):
- running `option` context rules on option CSV inputs (v1.1-B)
- option context binding / deterministic selection (v1.1-B / v1.1-C)
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

This sprint enables **typed validation** of `option` context rule files, but the runner does not execute them yet.

```bash
sigmadsl validate tests/fixtures/options/option_ok.sr
```

