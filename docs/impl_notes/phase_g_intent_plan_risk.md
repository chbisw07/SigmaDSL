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

## Sprint v2.0-B — Execution Planning IR

### Sprint goal

Introduce a deterministic, broker-agnostic Plan IR and a minimal CLI for generating it from effective intents:

- convert decision JSONL → effective intents → plan records
- preserve replay equivalence
- keep risk fail-closed (blocked intents become blocked plans)

### What was implemented

- **Plan IR schema**
  - implemented in `src/sigmadsl/plan_ir.py`
  - per-record schema:
    - `schema = sigmadsl.plan`
    - `schema_version = 2.0-b`

- **Planner**
  - implemented in `src/sigmadsl/planner.py`
  - `generate_plans(decisions, source=...)`:
    - consumes decision JSON dicts (from JSONL)
    - uses only `kind="intent"` with `is_effective=true`
    - blocked intents map to `status="blocked"` and carry `blocked_by`
    - overridden intents produce no plan record
    - deterministic ordering + deterministic plan ids (`P0001`, …)

- **CLI**
  - implemented in `src/sigmadsl/cli.py`
  - command:
    - `sigmadsl plan --input decisions.jsonl`
  - output:
    - JSON array of plan records (`sigmadsl.plan`)

### Tests / goldens

- `tests/test_plan_ir_v2_0_b.py`
  - schema correctness
  - declare → planned plan
  - cancel plan from effective cancel intent
  - overridden intents ignored
  - blocked intents → blocked plans
  - malformed JSONL rejected
  - replay equivalence: run vs replay produce identical plan output
- goldens:
  - `tests/golden/plan_basic.json`
  - `tests/golden/plan_conflict.json`

### Commands to run

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Manual workflow:

```bash
sigmadsl run --profile intent --input tests/fixtures/run/bars_one.csv --rules tests/fixtures/intents/intent_conflict.sr > /tmp/decisions.jsonl
sigmadsl plan --input /tmp/decisions.jsonl > /tmp/plans.json
```

Replay-safe workflow:

```bash
sigmadsl run --profile intent --input tests/fixtures/run/bars_one.csv --rules tests/fixtures/intents/intent_conflict.sr --log-out /tmp/runlog.json
sigmadsl replay --log /tmp/runlog.json > /tmp/decisions.jsonl
sigmadsl plan --input /tmp/decisions.jsonl > /tmp/plans.json
```

### Known limitations (intentionally deferred)

- no broker execution, routing, or venue selection
- no plan diff UX (beyond existing runlog diff)
- no portfolio optimization / multi-leg planning

---

## Sprint v2.0-C — Risk enforcement integrated (plan-time view)

### Sprint goal

Expose a deterministic, fail-closed risk view on top of the existing Intent→Plan flow without adding any execution semantics:

- add `sigmadsl plan --with-risk`
- include deterministic blocker reasons when available
- preserve replay parity for risk-aware planning
- do not change default `sigmadsl plan` output

### Policy (implemented)

- Default (`sigmadsl plan`):
  - unchanged v2.0-B output (`schema_version=2.0-b`)
- Risk-aware (`sigmadsl plan --with-risk`):
  - emits `schema_version=2.0-c`
  - every plan includes:
    - `risk.status`: `allowed` | `blocked` | `unknown`
    - `risk.blocked_by`
    - `risk.reasons`
  - fails closed if the input decision stream is missing `decision.enforcement.status` for an effective intent

### Reason extraction (implemented)

Sources:
- source intent decision:
  - `enforcement.status`
  - `enforcement.blocked_by`
- risk constraint decisions in the same stream (`kind="constraint"`, `profile="risk"`)

For each blocker id, a deterministic reason object is produced:
- `{ decision_id, rule_name, constraint_kind, reason }`

If a blocker id is present but the corresponding constraint decision is missing:
- the plan remains blocked
- the reason is recorded with `<missing>` placeholders (still fail-closed)

### Tests / goldens

- `tests/test_plan_risk_v2_0_c.py`
- goldens:
  - `tests/golden/plan_with_risk_allowed.json`
  - `tests/golden/plan_with_risk_blocked.json`
  - `tests/golden/plan_with_risk_conflict.json`

Replay parity test:
- run with `--log-out`, replay, then plan both with `--with-risk` and assert identical JSON.

### Commands

```bash
.venv/bin/python -m pytest -q

sigmadsl run --profile intent --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/intent_declare --risk-rules examples/risk_rules/packs/risk_cap_position > /tmp/decisions.jsonl
sigmadsl plan --input /tmp/decisions.jsonl --with-risk > /tmp/plans.json
```

### Deferred items

- broker execution / routing / OMS behavior
- plan-time optimization or multi-leg planning
