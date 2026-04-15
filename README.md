# SigmaDSL

SigmaDSL is a **Python-shaped** (indentation-based), **deterministic** rule DSL. It is **not Python** and is designed to be safely validated and executed without Python escape hatches.

This repository currently implements **Phase A** through **Sprint 0.2-A** (authoring bootstrap + type checker v1).

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Validate a rule file

```bash
sigmadsl validate path/to/file.sr
sigmadsl validate path/to/dir/   # validates all *.sr under the directory
```

Exit code is `0` for valid input and non-zero if any diagnostics are produced.

## Lint (Sprint 0.2-B)

Lint enforces guardrails (forbidden constructs) and current profile compliance:

```bash
sigmadsl lint path/to/file.sr
sigmadsl lint path/to/dir/
```

## Examples (Sprint 0.1-B)

Starter sample pack:

```bash
sigmadsl validate examples/equity_min_rules/
```

## Supported syntax (Sprint 0.1-A)

Minimal authoring subset aligned to `docs/DSL_v0.md` (Chapter 11 grammar sketch):

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

Supported structural keywords: `rule`, `in`, `when`, `elif`, `else`, `then`.

Type checking is implemented in **Sprint 0.2-A** for a minimal set of types/operators/verb arguments.

Not implemented yet (intentionally): evaluation/runtime, replay/diff, indicators, imports/packaging, options/chain, planning/risk.
