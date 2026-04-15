# SigmaDSL Quickstart (v0.1-A)

This quickstart covers **Sprint 0.1-A** only: **parsing + deterministic diagnostics** via `sigmadsl validate`.

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

## Limitations (intentional, for later sprints)

- expressions are parsed only shallowly for syntax shape (no typing or semantics)
- verbs are parsed as calls (no whitelist enforcement yet)
- no runtime/evaluation
- no imports/packaging, replay, indicators, planning, risk, options/chain
