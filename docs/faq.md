# SigmaDSL FAQ

## What is SigmaDSL?

SigmaDSL is a Python-shaped (indentation-based) DSL for expressing deterministic rule packs. It is designed to be validated, linted, and executed without Python escape hatches.

## How is it different from Python?

- SigmaDSL is **Python-shaped but not Python**: it borrows indentation and a familiar feel, but it is parsed by a dedicated grammar.
- It is **fail-closed**: forbidden constructs are rejected, and unsupported runtime behaviors raise deterministic errors.
- It is designed for **replayability** and stable outputs.

See `docs/language_guardrails.md` for the enforced constraints.

## What does “deterministic” mean here?

Given:
- the same rule sources,
- the same inputs (CSV bars),
- the same engine version,

SigmaDSL produces the same diagnostics, the same decisions, and the same trace outputs across runs.

This is enforced via stable ordering rules and verified by fixtures/goldens and replay/diff tooling.

## Why do `run` / `replay` / `diff` matter?

- `run` produces a decision stream from rules + inputs.
- `replay` reruns from a self-contained run log (embedded snapshots) to reproduce outputs deterministically.
- `diff` compares two runs deterministically and surfaces divergence.

See `docs/debugging_determinism.md`.

## What are `signal` / `intent` / `risk` profiles?

Profiles enforce separation of concerns:

- `signal`: emits `signal` / `annotation` decisions.
- `intent`: emits `intent` decisions (outputs only; no plan generation yet).
- `risk`: emits `constraint` decisions (used to block/limit prior decisions when provided as a separate risk pack).

See `docs/decision_profiles.md`.

## What does “fail-closed risk enforcement” mean?

When you run with a separate risk pack (`--risk-rules`), the engine applies constraints to prior decisions in a separate deterministic phase.

If a constraint applies, primary decisions are marked as blocked via:

- `enforcement.status = "blocked"`
- `enforcement.blocked_by = [<constraint decision ids>]`

See `docs/risk_constraints.md` and `examples/risk_rules/`.

## What is currently supported in the stable equity product?

The repo currently supports:

- parse/validate/lint + stable diagnostics
- deterministic evaluation on a minimal equity/bar input model
- stable decision schema (JSONL)
- explain/replay/diff workflows
- indicator registry (EMA/RSI/ATR/VWAP)
- deterministic imports and local pack bundling
- optional risk gating via a separate risk pack

See `docs/equity_product_quickstart.md`.

## What is intentionally not implemented yet?

Out of scope for current sprints:

- broker execution and routing
- plan generation from intent decisions
- portfolio-wide / stateful risk models
- options/chain support
- UI/frontend surfaces

