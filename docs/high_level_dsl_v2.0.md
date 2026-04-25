# High-level DSL v2.0 (implemented surface)

This is the **high-level** v2.0 document. It summarizes what v2.0 introduces at a product/platform level and is kept aligned to implementation.

For the authoritative spec snapshot, see `docs/dsl_v2.0.md`.

## v2.0 theme

v2.0 introduces the first explicit platform boundary for:

**Intent → Plan → Risk**

In **v2.0-A**, only the **Intent** layer is implemented.

## What v2.0-A adds (implemented)

### Intent verbs as first-class outputs (already present since v1.0-A)

Supported intent verbs remain intentionally minimal:
- `declare_intent(kind=..., quantity=..., percent=..., reason=...)`
- `cancel_intent(reason=...)`

### Deterministic intent resolution (new in v2.0-A)

For each `event_index`, raw intent decisions are resolved deterministically:

1. Idempotency collapse (deduplicate identical intents by a stable key)
2. Conflict resolution (deterministic winner selection)

Intent decision records now include:
- `is_effective`
- `overridden_by`

### Risk compatibility (preserved)

Risk phase (v1.0-B) remains a separate deterministic phase and stays fail-closed.

In v2.0-A:
- risk enforcement is applied only to **effective** intents
- overridden intents are ignored by the risk gate

## What is NOT implemented in v2.0-A

- no plan IR generation
- no routing or broker execution
- no portfolio optimization
- no new DSL syntax or new verbs

## What v2.0-B adds (implemented)

### Plan IR + `sigmadsl plan`

v2.0-B introduces a small broker-agnostic **Plan IR** output contract.

- Plan IR is generated from **effective intent decisions only**
- it is deterministic and replay-safe
- it carries no broker/exchange fields

CLI:

```bash
sigmadsl run --profile intent --input bars.csv --rules path/to/rules.sr > decisions.jsonl
sigmadsl plan --input decisions.jsonl > plans.json
```

See `docs/plan_ir.md`.

## What v2.0-C adds (implemented)

### Risk-aware planning (`sigmadsl plan --with-risk`)

v2.0-C integrates the existing fail-closed risk enforcement view into the Plan IR output surface (still broker-agnostic).

- `sigmadsl plan --with-risk` includes a `risk` section for every plan:
  - `risk.status`: allowed/blocked/unknown
  - `risk.blocked_by`
  - `risk.reasons` (derived deterministically from risk constraint decisions in the same stream)
- planning fails closed if required enforcement metadata is missing

## What v2.0-D adds (implemented)

### Parity harness (backtest / replay / simulated-live)

v2.0-D adds a parity harness that proves deterministic equivalence across:
- backtest mode (`sigmadsl run` on fixture inputs)
- replay mode (`sigmadsl replay --log ...`)
- simulated-live mode (deterministic event-by-event simulation over the same fixture inputs)

The parity harness is test-level (pytest) for now; no user-facing CLI is added in v2.0-D.

### Adapter contracts + integration guidance

v2.0-D documents adapter boundaries and integration guidance:
- SigmaDSL emits decisions and broker-agnostic Plan IR
- adapters are responsible for broker-specific mapping and execution lifecycle

See `docs/adapter_contracts.md`.

## Where to look

- Intent resolution logic: `src/sigmadsl/intent_resolution.py`
- Evaluator phase integration: `src/sigmadsl/evaluator.py`
- Intent output schema: `src/sigmadsl/decisions.py`
- Risk gating behavior: `src/sigmadsl/risk_constraints.py`
- Platform doc: `docs/intent_platform.md`
- Plan IR doc: `docs/plan_ir.md`
- Plan IR schema: `src/sigmadsl/plan_ir.py`
- Planner: `src/sigmadsl/planner.py`
- CLI: `src/sigmadsl/cli.py` (`sigmadsl plan`)
