# Plan IR (v2.0-B)

This document describes the **implemented** Plan IR introduced in **Sprint v2.0-B**.

Scope:
- deterministic conversion:
  - raw decisions JSONL → **effective intent decisions** → **Plan IR**
- broker-agnostic output only
- no routing and no broker execution

Out of scope (later sprints):
- plan execution / OMS integration
- routing, venue selection, exchange fields
- portfolio optimization

## What Plan IR is

Plan IR is a downstream-consumable record stream representing the platform’s **execution planning intent**.

In v2.0-B it is intentionally minimal:
- it is derived only from **effective intent decisions**
- it is produced by a separate CLI step (`sigmadsl plan`)
- it carries no broker/exchange fields

## What Plan IR is NOT

- it is not an order
- it does not execute anything
- it does not route to venues
- it does not allocate across accounts/portfolios

## Plan schema

Each plan record is a JSON object with:

- `schema`: `sigmadsl.plan`
- `schema_version`: `2.0-b` (default) or `2.0-c` (risk-aware planning)
- `plan_id`: deterministic id (e.g. `P0001`)
- `source_decision_id`: the intent decision id (e.g. `D0004`)
- `rule_name`, `event_index`, `symbol`, `timestamp`
- `intent_kind`
- `plan_action`: `declare` | `cancel`
- `size`: `{ quantity, percent }` (one or both may be null)
- `status`: `planned` | `blocked` | `skipped`
- `blocked_by`: list of constraint decision ids, or null

## Risk-aware planning (`--with-risk`) (v2.0-C)

`sigmadsl plan --with-risk` adds a deterministic, broker-agnostic risk view to every plan record.

In this mode:
- each plan includes a `risk` section:
  - `risk.status`: `allowed` | `blocked` | `unknown`
  - `risk.blocked_by`: list of blocking constraint decision ids (possibly empty)
  - `risk.reasons`: list of reason objects (possibly empty)
- if the input decision stream is missing `decision.enforcement.status`, planning **fails closed** with an error

Risk reason objects are derived deterministically from the same decision stream:

```json
{
  "decision_id": "D0002",
  "rule_name": "RISK: Cap max position 50",
  "constraint_kind": "max_position",
  "reason": "cap_50"
}
```

If a blocker id is present but the corresponding risk constraint decision is missing, the plan remains blocked and the reason is recorded with `<missing>` placeholders (still fail-closed).

## Generation rules (v2.0-B)

- only `kind="intent"` decisions are considered
- only `is_effective=true` intents produce plans
- overridden intents (`is_effective=false`) produce **no** plan record
- blocked intents (`enforcement.status="blocked"`) produce plans with:
  - `status="blocked"`
  - `blocked_by` populated from the intent’s `enforcement.blocked_by`
- ordering is deterministic and stable across reruns/replay

## CLI usage

Typical workflow:

```bash
sigmadsl run --profile intent --input bars.csv --rules path/to/rules.sr > decisions.jsonl
sigmadsl plan --input decisions.jsonl > plans.json
```

Replay-safe workflow:

```bash
sigmadsl run --profile intent --input bars.csv --rules path/to/rules.sr --log-out runlog.json
sigmadsl replay --log runlog.json > decisions.jsonl
sigmadsl plan --input decisions.jsonl > plans.json
```

Risk-aware workflow:

```bash
sigmadsl plan --input decisions.jsonl --with-risk > plans.json
```
