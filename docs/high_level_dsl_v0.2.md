# SigmaDSL — High-level DSL v0.2

Status: Implemented (typed authoring + guardrails lint).  
Scope: **Sprint 0.2-A** (“Type checker v1”) + **Sprint 0.2-B** (“Profile compliance + forbidden constructs”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.1.md`: v0.1 snapshot (authoring bootstrap: parse + deterministic diagnostics + examples)

This document describes what is **new or enforced** at the **v0.2 boundary**, based on implemented behavior in the repo.

## Supported language surface (v0.2)

The **structural grammar** remains the same as v0.1:

- `rule <name> in <context>:` blocks
- `when` with optional `elif` / `else`
- `then <verb_call(...)>` lines under each branch

### Expressions (parsed for typing)

In v0.2, expressions are parsed into a minimal AST to support type checking and better diagnostics.

Supported expression shapes (conservative subset):

- literals:
  - `true` / `false`
  - strings: `"..."` (double-quoted)
  - integers/decimals: `123`, `123.45`
  - percent literals: `0.2%` (types as `Percent`)
- names and dotted field access:
  - `data.is_fresh`, `bar.close`, `underlying.return_5m`
- function calls (whitelisted set only; see Guardrails):
  - `abs(x)`, `highest(close, 20)`, `lowest(close, 20)`, `prior_high(20)`, `prior_low(20)`
- operators:
  - boolean: `and`, `or`, `not`
  - comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - arithmetic (limited): `+`, `-`, `*`, `/`

Notes:
- chained comparisons (`a < b < c`) are rejected (use `and`)
- keyword arguments in expression function calls are rejected (v0.2 keeps calls simple)

## Validation / enforcement (v0.2)

### `sigmadsl validate` (parse + type check)

`validate` runs:

1. lex/parse (structural validation)
2. type checking **only if parse produced no diagnostics** (to avoid cascades)

Type checking enforces:

- branch conditions type as `Bool`
- boolean operators take boolean operands
- comparisons require compatible types
- verb calls have typed argument validation against minimal signatures

### Type model v1 (implemented)

The v0.2 type model is intentionally small and extensible:

- primitive-like: `Bool`, `String`, `Int`, `Decimal`, `Timestamp`, `Duration`
- domain types (initial set): `Price`, `Quantity`, `Percent`

Important principle (from `docs/DSL_v0.md`, Ch 12):

- **no implicit unit coercions** (`Price` is not `Decimal`)

To support practical authoring like `bar.close > 100`, the implementation uses **literal unification**:

- numeric literals can be compatible with certain domain types (e.g., `Price` vs `IntLiteral`)
- domain-to-domain coercions are still not performed

### Built-in field types (current minimal `underlying` context)

For v0.2 typing, only `underlying` context is supported with a minimal environment, including:

- `bar.open/high/low/close: Price`
- `bar.volume: Quantity`
- `bar.time: Timestamp`
- `data.is_fresh: Bool`
- `session.is_regular: Bool`
- `underlying.return_5m: Percent` (used by examples)

If a rule uses a context other than `underlying`, `validate` emits an error (v0.2 is equity/underlying-only so far).

### Verb signatures (current minimal set)

v0.2 validates verb call arguments for a minimal set of verbs:

- `emit_signal(kind: String, reason?: String, strength?: Decimal)`
- `annotate(note: String)`

Unknown verbs are rejected by `validate`.

## Linting / guardrails (v0.2)

### `sigmadsl lint` (guardrails + profile compliance)

`lint` checks:

- forbidden constructs (see below)
- function-call whitelist compliance
- current profile compliance (signal-only)

It accepts file or directory paths and produces deterministic diagnostics.

### Forbidden constructs (enforced by lint)

`sigmadsl lint` rejects:

- assignments (`SD400`)
- loops (`for`/`while`) (`SD401`)
- function definitions (`def`) (`SD402`)
- imports (`import` / `from`) (`SD405`)
- function calls outside a whitelist (`SD403`)

Note: because the parser is intentionally strict and minimal, some invalid constructs can also trigger
structural parse errors; lint output may include both parse diagnostics and lint diagnostics in a stable order.

### Language profiles (scaffolding)

SigmaDSL has conceptual profiles (`signal`, `intent`, `plan`, `risk`) per `docs/DSL_v0.md` Ch 10.

In v0.2:

- only `signal` is supported
- there is no explicit profile syntax yet, so lint treats all sources as `signal`
- verbs outside the signal allowlist are reported as profile violations (`SD410`)

## CLI / user-visible behavior (v0.2)

```bash
sigmadsl validate path/to/file.sr
sigmadsl lint path/to/file.sr
```

Both commands:

- accept file paths or directories (recursive `*.sr`)
- print `OK` on success
- print deterministic diagnostics on failure
- exit non-zero on failure

## Guardrails (v0.2)

SigmaDSL remains “Python-shaped but not Python”:

- no assignments/loops/user-defined functions/imports
- only whitelisted pure/deterministic expression functions
- verbs are explicit and validated (minimal set in v0.2)
- no broker execution inside the DSL

See `docs/language_guardrails.md` for the human-facing guardrails page.

## Known limitations / deferred items

Not implemented in v0.2 (intentionally deferred):

- evaluation/runtime semantics (no running strategies yet)
- trace, replay, diff
- indicators and numeric determinism policies (v0.5)
- imports/packaging (v0.6)
- option/chain contexts, intent/plan/risk semantics (v1.x / v2.0)
- editor/IDE features

## Examples

### Valid typed rule (underlying)

```sr
rule "EQ: Type OK" in underlying:
    when data.is_fresh and bar.close > 100:
        then emit_signal(kind="PASS", reason="fresh_and_close_gt_100", strength=0.7)
```

### Example type error

```sr
rule "EQ: Non Bool Condition" in underlying:
    when bar.close:
        then emit_signal(kind="X", reason="should_fail")
```

Expected shape of output:

```text
... SD300 error: Type mismatch in condition: expected Bool, got Price
```

### Example lint error (forbidden function call)

```sr
rule "EQ: Forbidden Function Call" in underlying:
    when now() > 0:
        then emit_signal(kind="X", reason="bad_fn")
```

Expected shape of output:

```text
... SD403 error: Forbidden function call (not whitelisted): 'now'
```

## Version summary (what changed in v0.2)

- Added expression AST parsing to enable deterministic type checking
- Added a minimal type model and type checker integrated into `validate`
- Added `lint` for guardrails + profile compliance with stable rule codes
