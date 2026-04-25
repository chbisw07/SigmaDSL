# Adapter contracts + integration guidance (v2.0-D)

This document defines the **implemented contract boundary** between SigmaDSL and downstream systems (e.g., broker adapters, OMS, SigmaTraderPRO).

SigmaDSL is **broker-agnostic** and **does not execute trades**.

## What SigmaDSL emits (and what it means)

SigmaDSL emits:

1) **Decisions** (`schema="sigmadsl.decision"`)
- signals, intents, risk constraints, annotations
- includes deterministic trace linkage and enforcement metadata

2) **Plan IR** (`schema="sigmadsl.plan"`)
- broker-agnostic planning records derived from **effective intent decisions**
- v2.0-B: `sigmadsl plan --input decisions.jsonl`
- v2.0-C: `sigmadsl plan --input decisions.jsonl --with-risk` (adds risk metadata)

SigmaDSL does **not**:
- place orders
- route to venues
- manage broker order lifecycle
- reconcile fills

## Adapter responsibilities (explicit boundary)

Adapters consume Plan IR and are responsible for all broker-specific concerns:

- mapping `symbol` to broker instrument identifiers
- mapping plan actions to broker order types (market/limit/etc.)
- mapping sizes (`size.quantity` / `size.percent`) to broker units and lot sizes
- broker-specific validation (tick sizes, margin limits, order restrictions)
- execution lifecycle (submit, amend, cancel, status polling)
- reconciliation (fills, partial fills, rejects)
- persistence and audit in the execution system

SigmaDSL intentionally does **not** attempt to model these behaviors.

## Handling risk and blocked plans

Adapters must treat:
- `status="blocked"` plans as **non-executable**

If an adapter cannot map a plan safely, it must fail closed (reject execution) rather than “best-effort” guessing.

### Risk-aware plans (`--with-risk`)

When `sigmadsl plan --with-risk` is used, each plan includes:

```json
"risk": {
  "status": "allowed|blocked|unknown",
  "blocked_by": ["D...."],
  "reasons": [
    {"decision_id": "...", "rule_name": "...", "constraint_kind": "...", "reason": "..."}
  ]
}
```

Adapters must not reinterpret:
- `risk.status="blocked"` as allowed
- `risk.status="unknown"` as allowed

## Correlation + idempotency (recommended)

Plan IR provides stable linkage for auditing and correlation:
- `plan_id`: deterministic within a plan output stream
- `source_decision_id`: stable linkage back to the intent decision that created the plan

Recommended adapter idempotency key (broker-side):
- `(runlog_sha256, plan_id)` if run logs are stored
  - or `(source_decision_id, plan_action, symbol, timestamp)` if only plan records are stored

Adapters should treat duplicate plan submissions with the same idempotency key as a no-op.

## Recommended storage (auditability)

Store the following artifacts per run:
- decision JSONL output (`decisions.jsonl`)
- run log (`sigmadsl.runlog`) produced via `sigmadsl run --log-out ...`
- plan JSON (`plans.json`) from `sigmadsl plan`
- risk-aware plan JSON (`plans_with_risk.json`) from `sigmadsl plan --with-risk`

This enables deterministic replay and parity checks:
- `sigmadsl replay --log ...` reproduces the exact decision stream
- plan generation from replayed decisions must match exactly

## Integration pipeline (recommended)

1. Author rules + validate/lint:
   - `sigmadsl validate ...`
   - `sigmadsl lint ...`
2. Produce decisions:
   - `sigmadsl run ... --log-out runlog.json > decisions.jsonl`
3. Produce plans:
   - `sigmadsl plan --input decisions.jsonl > plans.json`
4. Produce risk-aware plans:
   - `sigmadsl plan --input decisions.jsonl --with-risk > plans_with_risk.json`
5. Adapter consumes plan output and performs broker-specific work.

## What is intentionally deferred

- broker adapters in this repository
- exchange-specific execution semantics
- OMS lifecycle modeling
- routing logic
- portfolio optimization / multi-leg planning

