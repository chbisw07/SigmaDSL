# Decision profiles + stable decision schema (v1.0-A)

This page describes the **implemented** profile model and decision output contract introduced in **Sprint v1.0-A**.

Scope:
- explicit decision profiles: `signal`, `intent`, `risk`
- profile-specific verb allowlists
- stable decision JSON/JSONL schema for:
  - signals
  - intents
  - constraints (risk)
  - annotations
- deterministic trace linkage for every decision record

Out of scope (later sprints):
- real risk enforcement logic (blocking/limiting applied to other outputs)
- intent→plan generation / routing semantics
- broker execution

## Profiles (implemented model)

SigmaDSL uses profiles to enforce separation of concerns:

- `signal`: classify/label situations → emits signals and annotations
- `intent`: declare desired intent outputs (no execution planning yet)
- `risk`: emit constraints/blocks (outputs only in v1.0-A; enforcement is v1.0-B)

### Profile selection (current implementation)

v1.0-A does **not** add an in-language `profile` header yet. Instead, the profile is selected by the CLI:

```bash
sigmadsl validate path/to/rules.sr --profile signal
sigmadsl run --input bars.csv --rules path/to/rules.sr --profile signal
```

The default is `signal` for backward compatibility.

## Allowed verbs by profile (v1.0-A)

The allowlist is enforced deterministically during validation/linting and is fail-closed at runtime.

- `signal`:
  - `emit_signal(kind=..., reason=..., strength=...)`
  - `annotate(note=...)`
- `intent`:
  - `declare_intent(kind=..., quantity=..., percent=..., reason=...)`
  - `cancel_intent(reason=...)`
  - `annotate(note=...)`
- `risk`:
  - `constrain_max_position(quantity=..., reason=...)`
  - `block(reason=...)`
  - `annotate(note=...)`

## Stable decision schema (JSON/JSONL)

`sigmadsl run` and `sigmadsl replay` emit decisions as JSONL (one JSON object per line) or a JSON array (`--format json`).

Every decision record includes a stable envelope:
- `schema`: `sigmadsl.decision`
- `schema_version`: `1.0-b`
- `id`: stable decision id (e.g., `D0003`)
- `kind`: `signal` | `annotation` | `intent` | `constraint`
- `profile`: `signal` | `intent` | `risk`
- `verb`: the verb that produced the decision
- `rule_name`, `context`, `symbol`, `event_index`, `timestamp`
- `trace_ref`: `{ event_index, rule_name, action_index }`
- `enforcement`: `{ status, blocked_by }`

Sprint v1.0-C adds `sigmadsl report`, which consumes the same JSONL decision stream and aggregates outcomes per rule/symbol/day.

Kind-specific fields:
- `signal`:
  - `signal_kind`, `reason`, `strength`
- `annotation`:
  - `note`
- `intent`:
  - `intent_action` (`declare` or `cancel`)
  - `intent_kind`, `quantity`, `percent`, `reason`
- `constraint`:
  - `constraint_kind` (`max_position` or `block`)
  - `quantity`, `reason`

## Notes on limitations

### Risk enforcement (v1.0-B)

If you run with `--risk-rules`, the engine evaluates that rule pack in a separate risk phase and applies constraints
to prior decisions deterministically.

See `docs/risk_constraints.md` and `examples/risk_rules/` for the current behavior.

### Deferred items

- Intent outputs are **not** converted into execution plans (later).
