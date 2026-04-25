# Intent platform (v2.0-A)

This document describes the **implemented** intent-resolution platform boundary introduced in **Sprint v2.0-A**.

Scope:
- intent verbs remain the small v1 set: `declare_intent(...)`, `cancel_intent(...)`
- intents are resolved deterministically per event:
  - **idempotency collapse**
  - **conflict resolution**
- **no plan generation** and **no broker execution**

Out of scope (later sprints):
- intent → plan IR generation
- routing / broker-specific execution
- portfolio optimization / multi-leg execution semantics

## Intent phase in the pipeline

For every `event_index`, the engine now runs:

1. Emit raw decisions (signal/intent/annotation) from the selected profile pack
2. **Intent resolution** (only affects intent decisions)
3. Risk phase (if `--risk-rules` provided), applied to primary decisions

Intent resolution is intentionally a separate deterministic phase:

```
RAW INTENTS → IDEMPOTENCY → CONFLICT RESOLUTION → EFFECTIVE INTENTS
```

## Output schema additions (backward compatible)

Intent decisions now include:
- `is_effective`: `true` if the intent survives resolution and represents the effective intent for that event
- `overridden_by`: decision id (e.g. `D0004`) that overrode this intent, or `null`

The stable decision envelope remains:
- `schema`: `sigmadsl.decision`
- `schema_version`: `1.0-b`

## Idempotency rules

Idempotency key (per the v2.0-A contract):

```
(symbol, intent_kind, intent_action, quantity, percent)
```

If multiple intent decisions share the same idempotency key at an event:
- one is kept as effective
- others are marked:
  - `is_effective=false`
  - `overridden_by=<keeper decision id>`

Note: `reason` is **not** part of the idempotency key in v2.0-A.

## Conflict resolution rules

After idempotency collapse, the engine resolves conflicts deterministically.

Conflict policy (v2.0-A):
1. `cancel_intent` overrides `declare_intent`
2. larger absolute `quantity` wins
3. earlier rule order wins (deterministically approximated by earlier decision id)
4. `rule_name` lexical order tie-break

Winner remains `is_effective=true`.
Losers become `is_effective=false` and `overridden_by=<winner id>`.

## Risk compatibility

Risk enforcement remains fail-closed (v1.0-B), but now:
- risk constraints are applied only to **effective** intents
- overridden intents are ignored by the risk gate

## Example

If an event produces:
- multiple `declare_intent(kind="TARGET_LONG", quantity=100, ...)`
- one `declare_intent(kind="TARGET_LONG", quantity=200, ...)`
- one `cancel_intent(...)`

then the effective intent is the cancel, and all declares are marked overridden.

