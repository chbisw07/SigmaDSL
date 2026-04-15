# SigmaDSL

SigmaDSL is a **Python-shaped** (indentation-based), **deterministic** rule DSL. It is **not Python** and is designed to be safely validated and executed without Python escape hatches.

This repository currently implements **Sprint 0.1-A: Parse and diagnose** (authoring bootstrap).

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

## Supported syntax (Sprint 0.1-A)

Minimal authoring subset aligned to `docs/DSL_v0.md` (Chapter 11 grammar sketch):

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

Supported structural keywords: `rule`, `in`, `when`, `elif`, `else`, `then`.

Not implemented yet (intentionally): type checking, evaluation/runtime, replay/diff, indicators, imports/packaging, options/chain, planning/risk.
