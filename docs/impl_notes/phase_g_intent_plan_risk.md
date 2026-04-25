# Phase G — Intent → Plan → Risk (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md`.  
This document accumulates engineering notes for Phase G sprints (v2.0).

---

## Sprint v2.0-A — Intent verbs v1 (intent resolution)

### Sprint goal

Introduce a clean platform boundary for intent semantics without adding plan generation or broker execution:

- intent decisions remain first-class outputs (`declare_intent`, `cancel_intent`)
- a deterministic intent-resolution phase exists:
  - idempotency collapse
  - conflict resolution
- output schema exposes effective vs overridden intents
- risk phase remains separate and fail-closed, but ignores overridden intents

### What was implemented

- **Intent resolution module**
  - implemented in `src/sigmadsl/intent_resolution.py`
  - entrypoint: `resolve_intents_for_event(intent_list: list[IntentDecision]) -> list[IntentDecision]`
  - mutates passed intent decisions (by replacement) to set:
    - `is_effective`
    - `overridden_by`
  - returns only effective intents

- **Idempotency key (implemented)**
  - `(symbol, intent_kind, intent_action, quantity, percent)`
  - duplicates are marked overridden deterministically

- **Conflict resolution policy (implemented)**
  1. cancel overrides declare
  2. larger absolute `quantity` wins
  3. earlier rule order wins (approximated by earlier decision id)
  4. rule_name lexical tie-break

- **Evaluator pipeline integration**
  - `src/sigmadsl/evaluator.py` applies intent resolution per event for:
    - `evaluate_underlying`
    - `evaluate_option`
    - `evaluate_chain`
  - signal flow is unchanged

- **Schema extension (backward compatible)**
  - `src/sigmadsl/decisions.py` adds intent fields:
    - `is_effective`
    - `overridden_by`
  - decision `schema_version` remains `1.0-b`

- **Risk compatibility adjustment**
  - `src/sigmadsl/risk_constraints.py` ignores overridden intents (`is_effective=false`)
  - evaluator passes only effective intents into the risk gating call-site for extra safety

### Tests / goldens

- Unit + E2E tests in `tests/test_intent_resolution_v2_0_a.py`
  - duplicate collapse
  - cancel vs declare
  - quantity-based conflicts
  - deterministic tie-breaking
  - replay equivalence
  - CLI golden for a conflict case
- Goldens:
  - `tests/golden/run_intent.jsonl` (updated for new fields)
  - `tests/golden/run_intent_conflict.jsonl` (new)

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Manual conflict demo:

```bash
sigmadsl run --profile intent --input tests/fixtures/run/bars_one.csv --rules tests/fixtures/intents/intent_conflict.sr
```

Replay equivalence demo:

```bash
sigmadsl run --profile intent --input tests/fixtures/run/bars_one.csv --rules tests/fixtures/intents/intent_conflict.sr --log-out /tmp/intent_runlog.json
sigmadsl replay --log /tmp/intent_runlog.json
```

### Known limitations (intentionally deferred)

- no plan IR generation (intent→plan)
- no routing or broker execution
- no portfolio / multi-leg planning semantics
- no new verbs beyond `declare_intent` / `cancel_intent`

---

