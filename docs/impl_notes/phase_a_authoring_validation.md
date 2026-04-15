# Phase A — Authoring + Validation (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md` (project plan / roadmap).  
This document accumulates engineering notes for Phase A sprints (v0.1–v0.2).

---

## Sprint 0.1-A — Parse and diagnose

### Sprint goal

Deliver the first authoring bootstrap:

- `sigmadsl validate` parses a minimal DSL subset (rule blocks + branches + then-lines)
- invalid files produce **deterministic** diagnostics (stable ordering + stable format)
- foundation is established for v0.2 typing/profile validation without overbuilding v0.1

### What was implemented

- **Lexer**: indentation-aware tokenization with `INDENT`/`DEDENT`/`NEWLINE` and a minimal token set.
- **Parser**: minimal recursive-descent parser for the v0.x grammar sketch:
  - `rule "<name>" in <context>:` header
  - `when <expr>:` with optional `elif <expr>:` and optional `else:`
  - one or more `then <verb_call(...)>` lines under each branch
- **AST (minimal)**: rule/branch/then/verb-call structures with source spans (line/column).
- **Diagnostics model**: stable fields and stable sort order.
- **CLI**: `sigmadsl validate <path>` (file or directory) producing deterministic diagnostics and non-zero exit for errors.
- **Tests + fixtures**: valid/invalid `.sr` fixtures, parser tests, CLI tests, and golden-output snapshots for key error cases.

### Key design decisions

- **Hand-rolled lexer + parser** (not Python `ast`, not a general parser generator) to keep the DSL:
  - deterministic,
  - strictly “Python-shaped but not Python”,
  - easy to extend in future sprints without accidentally accepting Python constructs.
- **Expression handling is intentionally shallow** in v0.1-A:
  - expressions are tokenized and checked for basic shape (e.g., parentheses balance),
  - no typing, operator precedence semantics, or function/indicator whitelists yet.
- **Diagnostics are sorted** by `(file, line, column, code, message)` to guarantee stable output.

### Guardrails enforced (v0.1-A)

- Indentation defines blocks; tabs in indentation are rejected.
- Only declarative rule structure is accepted:
  - branch bodies must contain `then <verb_call(...)>` lines
  - unexpected statements inside branches produce deterministic errors
- No Python execution is possible (no `eval`, no importing Python, no runtime hooks).
- Assignments inside branch conditions are rejected with an explicit diagnostic (use `==`).

### Limitations intentionally left for next sprints

Not implemented in Sprint 0.1-A (by design):

- type checking / profiles / forbidden-construct enforcement at the AST level (Sprint 0.2)
- evaluator/runtime semantics, traces, replay/diff (v0.3+ / v0.4)
- indicators, caching, version pinning (v0.5)
- imports/packaging (v0.6)
- intent/planning/risk, options/chain (v1.x / v2.0)

### Commands to run

Install (dev):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Validate a sample fixture:

```bash
sigmadsl validate tests/fixtures/valid/basic_rule.sr
sigmadsl validate tests/fixtures/invalid/missing_colon_rule.sr
```

### Noteworthy implementation details

- Files validated in directory mode are discovered as `*.sr` and processed in sorted order for determinism.
- Diagnostic codes used in this sprint:
  - `SD100` unexpected character (lexing)
  - `SD101` indentation error
  - `SD200` syntax/structure parse errors (expected token/construct)
  - `SD201` missing required structure (e.g., missing `when`, missing `then`)
  - `SD203` unterminated string literal
- `SD204` forbidden construct (assignment-in-expr, forbidden statement starters)

---

## Sprint 0.1-B — Ship samples + docs

### Sprint goal

Turn the v0.1 parser into something a user can quickly try and understand:

- ship a starter sample pack of minimal equity rules,
- provide stable expected `validate` outputs for those samples,
- expand CLI snapshot/golden coverage to prevent regressions,
- keep changes incremental on top of Sprint 0.1-A (no redesign).

### What was added

- `examples/equity_min_rules/` sample pack (~10 `.sr` files) demonstrating:
  - single rule / multiple rules,
  - `when` + `then`,
  - multi-`then`,
  - `elif` / `else`,
  - comments/blank lines,
  - representative expression shapes (dot-access, calls, percent literal).
- Expected output artifact for validation success:
  - `examples/equity_min_rules/expected/validate_ok.txt` (`OK`).
- Expanded tests:
  - validate the examples directory output matches the expected artifact,
  - validate all example files parse cleanly,
  - add a deterministic **directory-validation golden** covering multiple failing files.
- Docs updates pointing users to `examples/`.

### `sigmadsl fmt` decision

Deferred in Sprint 0.1-B.

Reason: a formatter/indent-normalizer that is safe and deterministic would need a well-defined
pretty-printer and a policy for preserving comments/blank lines. With the current v0.1 AST
(which intentionally doesn’t preserve formatting trivia), a “rewrite formatter” would be lossy
and too risky for a low-scope sprint.

### Commands to run

Install (dev):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Validate the sample pack:

```bash
sigmadsl validate examples/equity_min_rules/
```

---

## Sprint 0.2-A — Type checker v1

### Sprint goal

Add typed authoring foundations while keeping the v0.1 parser/CLI stable:

- minimal type model (primitives + Price/Quantity/Percent/Timestamp/Duration),
- type checking for comparisons, boolean expressions, and verb argument types,
- improved diagnostics (expected vs got + useful spans),
- good/bad type fixtures and CLI goldens.

### What was implemented

- **Expression AST (v0.2)**:
  - expressions are parsed into a minimal AST (`src/sigmadsl/expr.py`) for typing and better error locations.
  - parser still controls structure (`rule`/`when`/`then`) and remains indentation-aware; only expression parsing was extended.
- **Type model v1** (`src/sigmadsl/types.py`):
  - `Bool`, `String`, `Int`, `Decimal`, `Timestamp`, `Duration`,
  - domain: `Price`, `Quantity`, `Percent`,
  - internal literal types to support numeric literals without unit coercions.
- **Built-in typing environment** (`src/sigmadsl/builtins.py`):
  - minimal `underlying` context field types per DSL spec (e.g., `bar.close: Price`, `data.is_fresh: Bool`),
  - a tiny whitelist of expression functions used in examples (`abs`, `highest`, `lowest`, `prior_high`, `prior_low`),
  - minimal verb signatures for `emit_signal(...)` and `annotate(...)`.
- **Type checker** (`src/sigmadsl/typechecker.py`):
  - conditions must type as `Bool`,
  - boolean ops require boolean operands,
  - comparisons require compatible types (with literal unification for numeric constants),
  - verb arguments are validated against signatures.
- **CLI integration**:
  - `sigmadsl validate` now performs parse + (if parse is clean) type checking.
  - parse diagnostics remain unchanged and continue to short-circuit type checking to avoid cascades.
- **Tests/fixtures**:
  - good/bad typecheck fixtures under `tests/fixtures/typecheck/`,
  - CLI golden tests for representative type errors.

### Key design decisions

- Introduced **literal type unification** (e.g., `bar.close > 100`) so numeric constants can type as `Price`/`Decimal`
  without converting between unit types (keeps “Price is not Decimal” intact).
- Kept the typed environment intentionally small and equity/`underlying`-only for v0.2-A.

### Diagnostic codes added (type checking)

- `SD300`: type mismatch / incompatible comparison
- `SD301`: unknown identifier/field/function
- `SD302`: operator not supported for operand types
- `SD303`: unsupported context for v0.2 type checking
- `SD310`–`SD313`: verb signature and argument typing errors

### Commands to run

```bash
pytest
sigmadsl validate tests/fixtures/typecheck/valid/ok_comparisons_and_args.sr
sigmadsl validate tests/fixtures/typecheck/invalid/non_bool_condition.sr
```

---

## Sprint 0.2-B — Profile compliance + forbidden constructs

### Sprint goal

Enforce “Python-shaped but not Python” guardrails and introduce profile scaffolding:

- forbid assignments, loops, function definitions, and non-whitelisted function calls,
- enforce `signal` profile only (future `intent`/`risk` recognized conceptually but not enabled),
- add `sigmadsl lint` with stable rule codes.

### What was implemented

- `sigmadsl lint` CLI:
  - lints a file or directory of `*.sr` files (deterministic ordering and output).
- Forbidden construct validation (lint):
  - assignment detection (`SD400`) via expression AST + statement-like assignment scanning,
  - loop detection (`SD401`) for `for`/`while` statement starters,
  - function definition detection (`SD402`) for `def` statement starters,
  - import detection (`SD405`) for `import`/`from` statement starters,
  - function-call whitelist enforcement (`SD403`) using the expression AST (`Call` nodes).
- Profile compliance (lint):
  - v0.2 treats all sources as `signal` and enforces a **signal-verb allowlist**.
  - non-signal verbs produce `SD410`.
- Tests:
  - fixtures under `tests/fixtures/lint/`,
  - CLI golden tests for stable rule codes and deterministic output.

### Commands to run

```bash
pytest
sigmadsl lint examples/equity_min_rules/
sigmadsl lint tests/fixtures/lint/invalid/assignment_in_condition.sr
```
