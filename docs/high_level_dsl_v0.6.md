# SigmaDSL — High-level DSL v0.6

Status: Implemented (deterministic imports + module layout).  
Scope: **Sprint 0.6-A** (“Imports + module layout”).

File role: High-level version summary (not a full spec copy-forward).

## Relationship to previous docs

- `docs/DSL_v0.md`: foundational design/spec (broad conceptual scope)
- `docs/high_level_dsl_v0.5.md`: v0.5 snapshot (indicators + sample strategies)
- `docs/dsl_v0.6.md`: spec snapshot for v0.6 (copy-forward with imports/module chapters concretized)

This document describes what is **new** at the **v0.6 boundary**, based on implemented behavior in the repo.

## What v0.6 adds (Sprint 0.6-A)

v0.6 introduces the first reusable rule-library structure:

- deterministic module naming from filesystem layout
- top-level `import ...` declarations (no Python import leakage)
- deterministic import closure resolution
- dependency graph validation with:
  - missing module diagnostics
  - cycle detection diagnostics
  - duplicate/ambiguous module mapping diagnostics

## Import model (implemented)

Syntax:

```sr
import lib.util

rule "..." in underlying:
    when true:
        then annotate(note="ok")
```

Resolution:

- pack root is the CLI path you pass (file parent or directory)
- `import foo.bar` resolves to `<root>/foo/bar.sr`
- cycles are rejected

See `docs/rule_library_layout.md` for the full layout rules and examples.

## CLI behavior (v0.6-A)

`sigmadsl validate`, `sigmadsl lint`, `sigmadsl run`, and `sigmadsl profile` now:

- resolve imports deterministically from the entry path
- validate the dependency graph and reject cycles
- then operate over the import closure

## Known limitations / deferred items

- packaging (`sigmadsl pack`) is Sprint 0.6-B
- no publish/install/registry workflows
- module metadata headers are deferred until packaging exists

