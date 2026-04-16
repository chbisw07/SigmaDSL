# Phase D — Library Reuse + Packaging (Implementation Notes)

Source of truth: `docs/DSL_v0.md` and `docs/02_dsl_proj_plan.md` (project plan / roadmap).  
This document accumulates engineering notes for Phase D sprints (v0.6).

---

## Sprint 0.6-A — Imports + module layout

### Sprint goal

Introduce a deterministic, minimal module/import model so rule packs can be reused as libraries:

- deterministic module name mapping from filesystem layout
- deterministic import resolution (no dynamic imports)
- dependency graph validation + cycle detection
- integrate imports into existing `validate`/`lint`/`run` flows
- fixtures + tests proving behavior and determinism

### Design choices (v0.6-A)

Import syntax:

- top-level only: `import foo.bar`
- no aliasing, no selective imports
- imports do **not** introduce Python semantics; they are rule-library structure only

Pack root:

- for a file input: pack root is the file’s parent directory
- for a directory input: pack root is that directory

Module mapping:

- `<root>/foo/bar.sr` → `foo.bar`
- `<root>/foo/__init__.sr` → `foo`
- `<root>/__init__.sr` → `__root__` (entry-only)

Dependency validation:

- missing import targets are errors (`SD601`)
- cycles are errors (`SD603`) with a stable reported cycle path
- ambiguous module name mappings are errors (`SD602`)

### What was implemented

- **Parser/AST support for import declarations**:
  - `src/sigmadsl/lexer.py` adds `IMPORT`
  - `src/sigmadsl/parser.py` parses top-level `import ...`
  - `src/sigmadsl/ast.py` adds `ImportDecl` and `SourceFile.imports`
- **Deterministic module loader + graph validator**: `src/sigmadsl/modules.py`
  - module indexing under pack root
  - import closure resolution
  - cycle detection
- **Integration**:
  - `sigmadsl validate` and `sigmadsl lint` now resolve imports and validate the graph
  - `sigmadsl run` and `sigmadsl profile` load only the import closure when given an entry file
- **Fixtures/tests**:
  - `tests/fixtures/imports/` packs for ok/missing/cycle/duplicate
  - `tests/test_imports.py` + goldens for error strings and runner output

### Commands to run

Run the full test suite:

```bash
.venv/bin/python -m pytest
```

Run only import-related tests:

```bash
.venv/bin/python -m pytest -k imports
```

Manual demo:

```bash
sigmadsl validate tests/fixtures/imports/pack_ok/main.sr
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/imports/pack_ok/main.sr
```

### Known limitations (intentionally deferred to 0.6-B and later)

- no packaging/bundles/manifests (`sigmadsl pack`) yet
- no publish/install/registry workflows
- no module-level metadata headers (will land with packaging)

---

## Sprint 0.6-B — Rule pack packaging

### Sprint goal

Add a local, deterministic packaging artifact so rule libraries can be bundled and verified:

- deterministic pack artifact format
- manifest model with name/version/compatibility + hashes
- `sigmadsl pack` command
- `sigmadsl validate --pack` command
- integrity/tamper detection tests

### Design choices (v0.6-B)

- container: deterministic zip (stored; stable ordering; fixed timestamps)
- contents:
  - `manifest.json`
  - `rules/...` (bundled `.sr` files for the import closure)
- hashing:
  - per-file sha256 recorded in `manifest.json`
  - validation fails closed on missing files or hash mismatches
- source validity:
  - `sigmadsl pack` requires syntax-clean sources (needed to compute an import closure deterministically)
  - type checking runs in `sigmadsl validate --pack` (matches `sigmadsl validate` semantics)
- compatibility:
  - `compat.dsl_spec` recorded (simple marker in v0.6-B)

### What was implemented

- Pack creation + validation:
  - `src/sigmadsl/packaging.py`
  - `sigmadsl pack ...`
  - `sigmadsl validate --pack ...`
- Tests:
  - `tests/test_packaging.py` creates packs in temp dirs and validates determinism/tamper detection

### Commands to run

Create a pack:

```bash
sigmadsl pack tests/fixtures/imports/pack_ok/main.sr --out pack_ok.zip --name pack_ok --version 0.1.0
```

Validate it:

```bash
sigmadsl validate --pack pack_ok.zip
```

### Known limitations (intentionally deferred)

- no signing/trust infrastructure
- no publish/install workflows or registries
