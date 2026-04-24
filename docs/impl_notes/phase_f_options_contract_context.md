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

