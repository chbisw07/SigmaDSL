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

