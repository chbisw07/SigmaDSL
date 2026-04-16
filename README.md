# SigmaDSL

SigmaDSL is a **Python-shaped** (indentation-based), **deterministic** rule DSL. It is **not Python** and is designed to be safely validated and executed without Python escape hatches.

This repository currently implements:

- **Phase A** through **Sprint 0.2-B** (authoring bootstrap + typed authoring + lint guardrails)
- **Phase B** through **Sprint 0.4-B** (CSV runner + JSON decisions + replay + diff + explain, verified via fixtures/goldens)
- **Phase C** through **Sprint 0.5-A** (indicator registry + deterministic windows + numeric goldens)

## DSL version docs

- `docs/DSL_v0.md` (base spec)
- `docs/high_level_dsl_v0.1.md` (v0.1 snapshot: parse/diagnose + samples/docs)
- `docs/high_level_dsl_v0.2.md` (v0.2 snapshot: type checker v1 + lint guardrails)
- `docs/high_level_dsl_v0.3.md` (v0.3 snapshot: deterministic evaluator + trace)
- `docs/high_level_dsl_v0.4.md` (v0.4 snapshot: event log + replay)
- `docs/high_level_dsl_v0.5.md` (v0.5 snapshot: indicator registry + deterministic windows)
- `docs/high_level_dsl_v0.6.md` (v0.6 snapshot: deterministic imports + module layout)

True spec version docs follow `docs/dsl_vX.Y.md` and are created only when a release requires
spec-level copy-forward updates beyond `docs/DSL_v0.md`.
Current spec snapshot docs:

- `docs/dsl_v0.3.md` (v0.3-A: deterministic evaluation + trace chapters concretized)
- `docs/dsl_v0.4.md` (v0.4-A: run log + replay semantics concretized)
- `docs/dsl_v0.5.md` (v0.5-A: indicator + window semantics concretized)
- `docs/dsl_v0.6.md` (v0.6-A: imports + library layout semantics concretized)

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

## Indicator examples (Sprint 0.5-B)

Indicator-based sample strategies + datasets + expected outputs:

```bash
sigmadsl validate examples/equity_indicator_rules/
sigmadsl run --input examples/equity_indicator_rules/data/bars_trend.csv --rules examples/equity_indicator_rules/packs/trend_following/
```

## Run (Sprint 0.3-B)

Run a rules file/directory against a minimal bars CSV (single symbol):

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

Explain a single decision:

```bash
sigmadsl explain --decision-id D0003 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

## Replay (Sprint 0.4-A)

Write a replay log during `run`:

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr --log-out runlog.json
```

Replay it deterministically:

```bash
sigmadsl replay --log runlog.json
```

## Diff + debug (Sprint 0.4-B)

Compare two run logs deterministically:

```bash
sigmadsl diff run_a.json run_b.json
```

See `docs/debugging_determinism.md` for the v0.4 replay+diff+explain workflow.

## Supported syntax (Sprint 0.1-A)

Minimal authoring subset aligned to `docs/DSL_v0.md` (Chapter 11 grammar sketch):

```sr
rule "EQ: Basic" in underlying:
    when true:
        then emit_signal(kind="BUY", reason="basic_true")
```

Supported structural keywords: `rule`, `in`, `when`, `elif`, `else`, `then`.

Type checking is implemented in **Sprint 0.2-A** for a minimal set of types/operators/verb arguments.

v0.3-A introduces a minimal deterministic evaluator + trace as a library surface (see `tests/test_evaluator_trace.py`).

Not implemented yet (intentionally): imports/packaging, broad indicator catalog, options/chain, planning/risk, multi-symbol evaluation.
