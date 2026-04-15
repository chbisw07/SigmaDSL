# SigmaDSL — High-level DSL v0.1

Status: Implemented (authoring bootstrap).  
Scope: **Sprint 0.1-A** (“Parse and diagnose”) + **Sprint 0.1-B** (“Ship samples + docs”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to `DSL_v0.md`

`docs/DSL_v0.md` is the foundational DSL design/spec document (full thesis-style scope).

This document is a **version snapshot** describing what the DSL and toolchain look like at the **v0.1 boundary**:

- what syntax is supported,
- what validation is enforced,
- what CLI behavior exists,
- what is explicitly deferred to later versions.

For later features (typing and lint guardrails), see `docs/high_level_dsl_v0.2.md`.

## Supported language surface (v0.1)

### File structure

A file contains one or more `rule` blocks. Blank lines and `#` comments are allowed.

### Rule blocks

Supported shape:

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

Rules support:

- `rule <name> in <context>:` header
  - `<name>` may be a string (`"..."`) or an identifier
  - `<context>` is parsed as an identifier (v0.1 does not enforce supported contexts)
- branches:
  - `when <expr>:`
  - optional `elif <expr>:`
  - optional `else:`
- actions:
  - one or more `then <verb_call(...)>` lines inside each branch block

### Expressions (authoring-only)

In v0.1, expressions are parsed **shallowly** for authoring validation:

- expressions are captured as token sequences up to `:` / `,` / `)`
- parentheses balance is checked
- **assignment (`=`) inside expressions is rejected** (use `==`)

No type checking or operator semantics are enforced at v0.1.

## Validation / enforcement (v0.1)

`sigmadsl validate` enforces:

- indentation-sensitive blocks (`rule` → branch → `then` lines)
- required structure (missing `when`, missing `then`, missing `:`) with deterministic errors
- deterministic diagnostics ordering
- rejection of:
  - tabs used for indentation
  - assignment-like `=` in expressions (guardrail)

Diagnostics format is stable and includes:

- file
- line
- column
- diagnostic code
- severity
- message

## CLI / user-visible behavior (v0.1)

### `sigmadsl validate`

```bash
sigmadsl validate path/to/file.sr
sigmadsl validate path/to/dir/
```

- directory mode recursively validates `*.sr` files in sorted order (deterministic)
- prints `OK` on success
- prints one diagnostic per line on failure
- exits `0` on success, non-zero on failure

## Guardrails (v0.1)

Even in v0.1, SigmaDSL is **Python-shaped but not Python**:

- no arbitrary Python execution
- no broker execution inside the DSL
- declarations are declarative rule blocks (not programs)
- authoring must remain deterministic and replay-friendly by design

## Known limitations / deferred items

Not part of v0.1 (deferred by roadmap):

- type checking (introduced in v0.2)
- explicit forbidden-construct linting (introduced in v0.2)
- evaluator/runtime, trace, replay/diff (v0.3+ / v0.4)
- indicators (v0.5)
- imports/packaging (v0.6)
- intent/plan/risk semantics, options/chain contexts (v1.x / v2.0)

## Examples

The shipped v0.1 sample pack is:

- `examples/equity_min_rules/`

Validate it:

```bash
sigmadsl validate examples/equity_min_rules/
```

## Version summary (what changed in v0.1)

- Implemented the first parseable DSL subset: `rule` + `when/elif/else` + `then <verb_call()>`
- Added deterministic diagnostics and a stable `validate` CLI
- Shipped an examples pack and docs so users can validate realistic minimal rules
