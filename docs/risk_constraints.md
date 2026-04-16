# Risk constraints v1 (v1.0-B)

This page describes the **implemented** risk constraint enforcement introduced in **Sprint v1.0-B**.

Scope:
- deterministic risk evaluation as a **separate phase**
- fail-closed blocking semantics (sprint-scoped)
- stable schema representation of blocked decisions
- runnable examples under `examples/risk_rules/`

Out of scope (later sprints):
- portfolio-wide risk models
- persistent stateful constraints across events
- intent→plan generation and plan-level enforcement

## Two-phase evaluation model (implemented)

In v1.0-B, a `run` can evaluate:

1. **Primary phase** (selected by `--profile`): produces `signal` or `intent` decisions.
2. **Risk phase** (optional): evaluates a separate **risk rule pack** and emits `constraint` decisions.

Then the engine applies the constraints to the primary decisions deterministically.

## CLI usage

Run signals with a risk pack:

```bash
sigmadsl run --profile signal --input bars.csv --rules path/to/signal_pack --risk-rules path/to/risk_pack
```

Run intents with a risk pack:

```bash
sigmadsl run --profile intent --input bars.csv --rules path/to/intent_pack --risk-rules path/to/risk_pack
```

`sigmadsl replay` reproduces the same behavior because risk rule sources are embedded in the run log.

## Implemented constraints (v1.0-B)

The v1.0-B engine applies only sprint-scoped constraints:

- `block(reason=...)`:
  - blocks **all primary decisions** at the same event index
- `constrain_max_position(quantity=..., reason=...)`:
  - blocks `declare_intent(...)` decisions whose `quantity` exceeds the max

Any unsupported/unknown constraint kinds are treated as **block-all** (fail-closed).

## How blocked decisions are represented

Every decision record includes an `enforcement` section:

- `enforcement.status`: `allowed` or `blocked`
- `enforcement.blocked_by`: list of constraint decision ids that caused the block

The blocking constraint decisions are also present in the same JSONL stream as `kind="constraint"`.

## Examples

See `examples/risk_rules/README.md` for runnable scenarios and expected outputs.

