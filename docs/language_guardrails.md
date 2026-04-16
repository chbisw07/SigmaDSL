# SigmaDSL Language Guardrails (v0.2)

SigmaDSL is **Python-shaped** (indentation-based) for readability, but it is **not Python**.
The language is designed to be:

- **deterministic** (replayable, stable outputs),
- **declarative** (rules produce decisions, not programs),
- **safe** (no escape hatches into arbitrary execution).

These guardrails are core to the roadmap and are enforced by `sigmadsl lint` and `sigmadsl validate`.

Source-of-truth chapters:
- `docs/DSL_v0.md`: Ch 2.6 (constraints), Ch 10 (profiles), Ch 11 (syntax), Ch 12 (validation pipeline)
- `docs/02_dsl_proj_plan.md`: Phase A and Sprint 0.2-B (“Profile compliance + forbidden constructs”)

---

## What is forbidden (and why)

### Assignments

Not allowed:

```sr
when x = bar.close:
```

Reason: assignments introduce mutable state and “program-like” behavior that breaks the rule/decision model.

### Loops

Not allowed:

```sr
for i in range(10):
```

Reason: loops can hide unbounded computation and non-obvious ordering; they also push the DSL toward general-purpose scripting.

### Function definitions

Not allowed:

```sr
def helper(x):
```

Reason: user-defined functions expand the language surface dramatically and create execution/validation ambiguity.

### Function calls outside a whitelist

Allowed calls are strictly whitelisted pure/deterministic functions (a small set in v0.2).
Calls like `now()` / `random()` are rejected.

Reason: non-deterministic or side-effecting calls are incompatible with replayability and auditability.

---

## Language profiles (signal / intent / plan / risk)

SigmaDSL defines conceptual profiles:

- `signal`: emit classifications/signals
- `intent`: express intent outputs (no planning yet)
- `plan`: generate broker-agnostic plans (deferred)
- `risk`: express constraints/blocks (enforcement deferred)

In **v1.0-A**, `signal`, `intent`, and `risk` profiles are supported as **validation + output contracts**.
Profile selection is currently done via the CLI `--profile` flag (there is not yet an in-language profile header).

See `docs/decision_profiles.md` for the implemented verb allowlists and output schema.

---

## CLI: `lint` vs `validate`

- `sigmadsl lint <path>`: guardrails + profile compliance (forbidden constructs, verb allowlist, function-call whitelist)
- `sigmadsl validate <path>`: parse + type check + profile compliance

Both commands accept a file path or a directory (recursively validates/lints `*.sr`).

---

## Diagnostic codes (selected)

Parse/structure (existing):
- `SD200`: syntax/structure error
- `SD201`: missing required structure

Type checking (Sprint 0.2-A):
- `SD300`–`SD313`: type errors and verb signature typing errors

Guardrails / lint (Sprint 0.2-B):
- `SD400`: forbidden assignment
- `SD401`: forbidden loop
- `SD402`: forbidden function definition
- `SD403`: forbidden function call (not whitelisted)
- `SD405`: forbidden import
- `SD410`: profile violation (verb not allowed for selected profile)
