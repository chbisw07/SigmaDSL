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
  - decision envelope: `schema="sigmadsl.decision"`, `schema_version="1.0-a"`
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

