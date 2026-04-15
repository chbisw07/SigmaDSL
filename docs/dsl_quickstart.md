# SigmaDSL Quickstart (v0.1-A)

This quickstart covers **Phase A early sprints**:

- **Sprint 0.1-A**: parsing + deterministic diagnostics
- **Sprint 0.1-B**: sample pack + docs
- **Sprint 0.2-A**: type checker v1 (comparisons/boolean ops/verb argument types)

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Write a minimal rule file

Create `basic.sr`:

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

## Validate it

```bash
sigmadsl validate basic.sr
```

Expected output:

```
OK
```

## Lint guardrails (v0.2-B)

Run lint to enforce “Python-shaped but not Python” guardrails:

```bash
sigmadsl lint basic.sr
```

Expected output:

```text
OK
```

## Try the sample pack (v0.1-B)

Sprint v0.1-B ships a starter sample pack under `examples/`:

```bash
sigmadsl validate examples/equity_min_rules/
```

Expected output:

```text
OK
```

## What `validate` checks in v0.1-A

- indentation-sensitive blocks (`rule` → branch → `then` lines)
- required structure:
  - `rule "<name>" in <context>:`
  - `when <expr>:` (with optional `elif` / `else`)
  - one or more `then <verb_call(...)>` lines under each branch
- deterministic diagnostics with: file, line, column, code, severity, message

## Type checking (v0.2-A)

`sigmadsl validate` also runs a conservative v1 type checker:

- conditions must type as `Bool`
- boolean operators (`and`/`or`/`not`) require boolean operands
- comparisons require compatible types (e.g., `Price` vs `Price`, `Percent` vs `Percent`)
- verb calls (`then ...`) have typed argument checks for a minimal verb set

Example type error:

```sr
rule "EQ: Bad" in underlying:
    when bar.close:
        then emit_signal(kind="X", reason="should_fail")
```

```text
... SD300 error: Type mismatch in condition: expected Bool, got Price
```

## Language guardrails (v0.2-B)

See `docs/language_guardrails.md` for a concise explanation of:

- forbidden constructs (assignments, loops, function defs),
- function-call whitelist rules,
- profile compliance (signal-only in v0.2).

## Limitations (intentional, for later sprints)

- no evaluator/runtime semantics (type checking only; no execution)
- expression/function and verb signature sets are intentionally minimal and will expand later
- no imports/packaging, replay, indicators, planning, risk, options/chain
