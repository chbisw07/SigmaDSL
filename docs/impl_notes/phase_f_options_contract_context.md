# Phase F — Options Contract Context (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md`.  
This document accumulates engineering notes for Phase F sprints (v1.1).

---

## Sprint v1.1-A — Option instrument model + types

### Sprint goal

Establish a deterministic, validated option contract foundation:

- option contract identity model
- canonical contract identifiers (broker-agnostic)
- option snapshot input model (quotes + optional greeks)
- explicit freshness/quality guard fields
- fixtures/tests for expiry/strike parsing and validation

### What was implemented

- **Canonical option id format + validation**
  - implemented in `src/sigmadsl/options_contracts.py`
  - format: `OPT:<VENUE>:<UNDERLYING>:<EXPIRY>:<STRIKE>:<RIGHT>:<LOT>`
  - strict parsing:
    - expiry: `YYYY-MM-DD`
    - strike: decimal with at most 2 dp (no fuzzy rounding)
    - right: `CALL`/`PUT` (also accepts `C/P` and `CE/PE`, normalized)
    - lot: integer `> 0`
- **Option snapshot model**
  - implemented in `src/sigmadsl/options_snapshots.py`
  - atomic per-contract snapshot with quote + optional greeks fields
  - explicit `data_is_fresh` and `quality_flags`
  - fixed quantization for IV/greeks to keep fixture outputs reproducible
- **Typed validation for `option` context**
  - `sigmadsl validate` now type-checks rules with `in option:` using an explicit option field environment
  - runner execution for option snapshots is intentionally deferred to v1.1-B

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Validate an option-context rule (typed only):

```bash
sigmadsl validate tests/fixtures/options/option_ok.sr
```

### Known limitations (intentionally deferred)

- no `sigmadsl run --input options.csv` mode yet (v1.1-B)
- no option context binding / selection helpers yet (v1.1-B / v1.1-C)
- no chain snapshot semantics or chain-derived metrics (v1.2+)

---

## Sprint v1.1-B — Option context binding

### Sprint goal

Make `in option:` rules runnable:

- runtime option context binding (contract-level atomic snapshots)
- deterministic option snapshot selection (fail closed on ambiguity)
- option snapshot CSV input support in `sigmadsl run`
- replay support for option-context runs

### What was implemented

- **Runtime option events**
  - `src/sigmadsl/options_runtime.py` introduces `OptionEvent` (atomic contract snapshot event).
- **Option CSV loader**
  - `src/sigmadsl/csv_input.py` adds a strict option snapshot CSV loader:
    - required columns: `contract_id`, `timestamp`
    - optional quote + IV/greeks columns (parsed deterministically as `Decimal`)
    - deterministic selection:
      - single-contract CSVs run directly
      - multi-contract CSVs require `--contract-id` (fail closed without it)
    - explicit identity cross-checks when `venue/underlying/expiry/strike/right/lot` columns are present.
- **Runtime binding**
  - `src/sigmadsl/evaluator.py` now supports `evaluate_option(...)` and an option runtime environment mapping:
    - `option.*` fields resolve from the bound snapshot
    - unknown fields fail closed at runtime (deterministic `EvalError`)
- **CLI integration**
  - `sigmadsl run` and `sigmadsl explain` accept `--context underlying|option` and `--contract-id` for option mode.
- **Replay compatibility**
  - option runs can be logged and replayed deterministically:
    - run log records `input.kind=option` and embedded option snapshot events
    - replay uses the recorded kind to rerun the same evaluation.
- **Examples + tests**
  - runnable example pack: `examples/option_context_rules/`
  - end-to-end CLI goldens for option runs, selection ambiguity, and data-quality rejection

### Data quality / fail-closed boundary

The option runner rejects unusable snapshots (fail closed):
- `data_is_fresh=false`
- missing quote data
- non-empty `quality_flags`

This is conservative by design for v1.1-B; future sprints can refine quality flag semantics.

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run the option context example:

```bash
sigmadsl run --context option --input examples/option_context_rules/data/options_basic.csv --rules examples/option_context_rules/option_signals.sr
```

Replay an option run:

```bash
sigmadsl run --context option --input examples/option_context_rules/data/options_basic.csv --rules examples/option_context_rules/option_signals.sr --log-out /tmp/opt_runlog.json
sigmadsl replay --log /tmp/opt_runlog.json
```

### Known limitations (intentionally deferred)

- option chain context (`in chain:`) and derived chain metrics (v1.2+)
- fuzzy broker symbol matching (explicit canonical ids only)

---

## Sprint v1.1-C — Selection helpers + examples

### Sprint goal

Add deterministic selection helpers over **explicit option snapshot inputs** so users can run a multi-contract bundle
without manually specifying `--contract-id`:

- ATM selection
- nearest OTM selection
- delta-based selection (when delta is present)

### What was implemented

- **Selection helper layer**
  - `src/sigmadsl/options_selection.py` defines a small selection request + deterministic tie-breakers.
- **CSV selection entrypoint**
  - `src/sigmadsl/csv_input.py` adds `select_option_contract_id_from_csv(...)`:
    - selection timestamp = earliest CSV timestamp (lexicographic min)
    - candidates = usable snapshots at that timestamp (one per contract)
    - fails closed on ambiguity, missing required fields, or no usable candidates
- **CLI integration**
  - `sigmadsl run` / `sigmadsl explain` (option context) now accept:
    - `--select atm|otm|delta`
    - `--right CALL|PUT`
    - `--expiry YYYY-MM-DD` (optional candidate filter)
    - `--otm-rank N` (nearest is `1`)
    - `--target-delta <decimal>` for delta selection
- **Required inputs**
  - ATM/OTM selection requires `underlying_price` on candidate rows.
  - delta selection requires `delta` on candidate rows.
- **Examples**
  - `examples/options_contract_rules/` demonstrates selection helpers with expected outputs.
- **Tests**
  - CLI goldens cover:
    - ATM/OTM/delta selection outputs
    - tie-breakers (earlier expiry)
    - fail-closed errors for missing underlying_price / missing delta / missing right / bad quality
    - replay equivalence for selection-driven runs

### Tie-breakers (deterministic)

1) primary distance metric (ATM strike distance / OTM distance / delta distance)  
2) earlier expiry  
3) right order (CALL before PUT)  
4) canonical contract id lexical order

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run selection examples:

```bash
sigmadsl run --context option --select atm --right CALL --input examples/options_contract_rules/data/options_bundle.csv --rules examples/options_contract_rules/option_selected_echo.sr
sigmadsl run --context option --select otm --right CALL --input examples/options_contract_rules/data/options_bundle.csv --rules examples/options_contract_rules/option_selected_echo.sr
sigmadsl run --context option --select delta --right CALL --target-delta 0.68 --input examples/options_contract_rules/data/options_bundle.csv --rules examples/options_contract_rules/option_selected_echo.sr
```

### Known limitations (intentionally deferred)

- chain-derived analytics (PCR/max pain/skew/OI concentration/etc.) remain deferred (v1.2-A delivers chain snapshot *quality* only)
- no per-bar dynamic contract reselection (that becomes chain context)
- no fuzzy broker symbol matching (explicit canonical ids only)

---

## Sprint v1.2-A — Chain schema + snapshot semantics

### Sprint goal

Introduce a minimal, deterministic **chain snapshot** input model and runnable `chain` context:

- strict atomic chain snapshot schema
- strict chain CSV loader (grouped by snapshot timestamp)
- first-class quality predicates for author guardrails
- deterministic Unknown policy for incomplete chain snapshots
- run/replay support for `--context chain`

### What was implemented

- **Chain snapshot schema**
  - `src/sigmadsl/chain_snapshots.py` introduces `ChainSnapshot` with an explicit schema/version:
    - `schema="sigmadsl.chain_snapshot"`, `schema_version="1.2-a"`
  - the snapshot embeds per-contract `OptionSnapshot` rows (v1.1) and carries explicit:
    - `data_is_fresh`, `quality_flags`, `is_complete`, `has_unknowns`
- **Chain runtime event**
  - `src/sigmadsl/chain_runtime.py` introduces `ChainEvent` (atomic chain snapshot event).
- **Chain CSV loader**
  - `src/sigmadsl/csv_input.py` adds a strict loader:
    - required columns: `snapshot_timestamp`, `contract_id`
    - groups rows by snapshot timestamp into atomic chain events
    - rejects duplicate `contract_id` within a snapshot (fail closed)
    - rejects mixed venues/underlyings within a snapshot (fail closed)
    - parses each row through the v1.1 option snapshot parser for consistent normalization
- **Typed `in chain:` environment**
  - `src/sigmadsl/builtins.py` and `src/sigmadsl/typechecker.py` add a minimal `chain.*` environment:
    - timestamp: `chain.as_of` (with `chain.time` as an alias)
    - quality: `chain.is_fresh`, `chain.is_complete`, `chain.has_unknowns`, `chain.quality_ok`
- **Deterministic evaluation + Unknown policy**
  - `src/sigmadsl/evaluator.py` adds `evaluate_chain(...)`:
    - only quality predicates + action emission (no analytics)
    - if `chain.has_unknowns` is true:
      - predicates that don’t mention chain quality fields are recorded as **Unknown** and do not match
      - `else` branches are disabled (fail closed)
- **CLI + replay**
  - `sigmadsl run` supports `--context chain`
  - `--log-out` records `input.kind=chain` and embeds chain snapshot events
  - `sigmadsl replay` replays chain runs deterministically from the embedded snapshots
- **Examples + tests**
  - example pack: `examples/option_chain_context/`
  - CLI goldens + replay equivalence tests for chain context fixtures

### Diagnostics (selected)

- chain CSV header/shape:
  - `SD760`: missing header/required columns
  - `SD761`: empty `snapshot_timestamp`
  - `SD762`: duplicate `contract_id` within a snapshot group
  - `SD763` / `SD764`: mixed venue/underlying within a snapshot group
- runner:
  - `SD780`: no `in chain:` rules found in a pack

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run the chain example:

```bash
sigmadsl run --context chain --input examples/option_chain_context/data/chain_demo.csv --rules examples/option_chain_context/chain_quality.sr
```

Explain an Unknown predicate result (incomplete chain snapshot):

```bash
sigmadsl explain --context chain --rule "CHAIN: Unconditional" --event-index 0 --input tests/fixtures/chain/chain_incomplete.csv --rules tests/fixtures/chain/chain_unknown_policy.sr
```

Replay a chain run:

```bash
sigmadsl run --context chain --input tests/fixtures/chain/chain_complete.csv --rules tests/fixtures/chain/chain_ok.sr --log-out /tmp/chain_runlog.json
sigmadsl replay --log /tmp/chain_runlog.json
```

### Known limitations (intentionally deferred)

- no chain-derived metrics or analytics in expressions yet (PCR/max pain/skew/etc.)
- no per-contract chain iteration (`chain.contracts[...]`) or aggregations yet
- no option chain live ingestion (fixtures/CSV only)
