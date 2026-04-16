# Phase E — Stable Equity Product (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md` (project plan / roadmap).  
This document accumulates engineering notes for Phase E sprints (v1.0).

---

## Sprint v1.0-A — Signal / Intent / Risk profiles

### Sprint goal

Establish a stable “product contract” boundary for downstream consumers:

- explicit decision profiles: `signal`, `intent`, `risk`
- profile-specific verb allowlists
- stable decision output schema with deterministic trace linkage
- golden tests protecting the output contract

### Design choices (v1.0-A)

- **Profile selection (CLI-only):**
  - no in-language `profile` header yet
  - `sigmadsl validate/lint/run` accept `--profile {signal|intent|risk}` (default: `signal`)
- **Verb allowlists (enforced deterministically):**
  - `signal`: `emit_signal`, `annotate`
  - `intent`: `declare_intent`, `cancel_intent`, `annotate`
  - `risk`: `constrain_max_position`, `block`, `annotate`
- **Stable decision schema:**
  - decision envelope: `schema="sigmadsl.decision"` (v1.0-A introduced `1.0-a`; v1.0-B bumps to `1.0-b` for enforcement fields)
  - per-decision `trace_ref={event_index, rule_name, action_index}` for stable linkage to trace
  - `kind` widened to include `intent` and `constraint` (in addition to `signal` and `annotation`)
- **Backward-compat:**
  - legacy top-level fields remain present in decision JSON objects (e.g., `id`, `kind`, `rule_name`, `symbol`, `event_index`, `timestamp`)
  - run logs now record `profile` and `decision_schema` metadata; older logs remain loadable

### What was implemented

- Profile model + schema constants: `src/sigmadsl/decision_profiles.py`
- Profile compliance validator: `src/sigmadsl/profile_compliance.py`
- New decision kinds and stable envelope: `src/sigmadsl/decisions.py`
- Runtime support for intent/constraint verbs as outputs (no enforcement): `src/sigmadsl/evaluator.py`
- CLI integration:
  - `sigmadsl validate --profile ...`
  - `sigmadsl lint --profile ...`
  - `sigmadsl run --profile ...`
  - run logs record the selected profile (`src/sigmadsl/runlog.py`)
- Goldens + schema tests:
  - updated `tests/golden/run_*.jsonl`, `tests/golden/explain_*.txt`, `tests/golden/diff_*.txt`
  - added schema contract checks (`tests/test_decision_schema_v1_0_a.py`)
  - added intent/risk profile fixture tests (`tests/test_profiles_v1_0_a.py`)

### Commands to run

Run the full test suite:

```bash
.venv/bin/python -m pytest
```

Manual demos:

```bash
sigmadsl run --profile signal --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
sigmadsl run --profile intent --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/profiles/intent_ok.sr
sigmadsl run --profile risk --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/profiles/risk_ok.sr
```

### Known limitations (intentionally deferred)

- risk constraints are **not enforced** against other outputs yet (Sprint v1.0-B)
- intent outputs are not converted into plans (later)
- no in-language `profile` header yet (CLI-only in v1.0-A)

---

## Sprint v1.0-B — Risk constraints v1

### Sprint goal

Add a separate deterministic risk phase that can block prior decisions in a fail-closed way:

- evaluate a risk rule pack after primary decision generation
- apply constraint decisions to prior decisions deterministically
- represent blocked outcomes in the stable decision schema
- add runnable `examples/risk_rules/` and replayable goldens

### Design choices (v1.0-B)

- **Separate risk pack**:
  - primary rules are evaluated under `--profile {signal|intent}`
  - risk rules are evaluated from `--risk-rules <path>` under profile `risk`
- **Fail-closed constraint semantics (sprint-scoped)**:
  - `block(reason=...)` blocks all primary decisions at the same event index
  - `constrain_max_position(quantity=..., ...)` blocks `declare_intent(...)` when `quantity` exceeds the max
  - unknown/unsupported constraint kinds are treated as block-all
- **Stable schema integration**:
  - every decision includes `enforcement={status, blocked_by}`
  - blocked decisions list the constraint decision ids in `blocked_by`
- **Replay**:
  - run logs embed the risk rule sources under `risk.rules.files[]`
  - `replay` reproduces risk-applied outputs deterministically

### Commands to run

Run the full test suite:

```bash
.venv/bin/python -m pytest
```

Manual demo (signal blocked):

```bash
sigmadsl run --profile signal --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/signal_always --risk-rules examples/risk_rules/packs/risk_block_close
```

### Known limitations (intentionally deferred)

- no portfolio-wide or stateful risk enforcement (event-local only)
- no plan generation or routing

---

## Sprint v1.0-C — Reports + UX polish

### Sprint goal

Improve usability on top of the stable equity CLI surface:

- add `sigmadsl report` for practical aggregates (rule / symbol / day)
- polish `sigmadsl explain` output for “why did / didn’t it fire?”
- add equity-focused quickstart + FAQ

### What was implemented

- **Report command:**
  - `sigmadsl report --input decisions.jsonl` aggregates:
    - total decision counts
    - allowed vs blocked counts (via `enforcement.status`)
    - grouping by `(day, symbol, rule_name)` with kind breakdown
  - deterministic ordering and golden-backed output
- **Explain UX:**
  - decision explains now surface `enforcement` in the header
  - blocked decisions list the blocking constraint decision ids and a one-line constraint summary
- **Docs:**
  - `docs/equity_product_quickstart.md`
  - `docs/faq.md`

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest
```

Manual report demo:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr > decisions.jsonl
sigmadsl report --input decisions.jsonl
```

Manual explain demo (blocked decision):

```bash
sigmadsl explain --decision-id D0001 --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/signal_always --risk-rules examples/risk_rules/packs/risk_block_close
```

### Known limitations (intentionally deferred)

- reports are intentionally minimal (no PnL, no broker/execution metrics)
- report consumes decision JSONL only (it does not ingest run logs directly)
