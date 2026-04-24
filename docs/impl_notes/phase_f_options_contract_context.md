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
- automatic contract selection helpers (ATM/weekly selection, etc.)
- fuzzy broker symbol matching (explicit canonical ids only)
