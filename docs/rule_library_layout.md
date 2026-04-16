# Rule library layout + imports (v0.6-A)

This page describes the **implemented** rule-library layout and deterministic import model introduced in **Sprint v0.6-A**.

Scope:
- deterministic imports and module resolution
- dependency graph validation + cycle detection

Out of scope (v0.6-B and later):
- packaging/bundles/manifests (`sigmadsl pack`)
- publish/install workflows or registries

## Key principles

- **Python-shaped, not Python**: imports exist for rule-library structure, not for arbitrary Python modules.
- **Deterministic resolution**:
  - no dynamic import paths
  - no globbing
  - no environment-dependent behavior
- **Fail-closed**: missing modules, ambiguous modules, and cycles are hard errors.

## Module layout model

A “pack root” is determined by the CLI path you pass:

- if you pass a **file** path, the pack root is the file’s parent directory
- if you pass a **directory** path, the pack root is that directory

All `.sr` files under the pack root are potential modules.

### Module name mapping

Module names map deterministically from filesystem paths:

- `<root>/foo/bar.sr` → module name `foo.bar`
- `<root>/foo/__init__.sr` → module name `foo`
- `<root>/__init__.sr` → module name `__root__` (entry-only; not intended as an import target)

### Duplicate/ambiguous modules

If two different files map to the same module name, validation fails.

Example ambiguous mapping:

- `<root>/foo.sr` (module `foo`)
- `<root>/foo/__init__.sr` (module `foo`)

This fails with `SD602`.

## Import syntax (v0.6-A)

Imports are top-level declarations only:

```sr
import lib.util

rule "..." in underlying:
    when true:
        then annotate(note="ok")
```

Rules:
- only `import <dotted.module.path>` is supported
- no aliasing (`as`), no selective imports, no star imports
- imports are **not allowed** inside `rule` blocks

## Import resolution rules

`import lib.util` resolves to:

- module name `lib.util`
- file path `<root>/lib/util.sr`

Errors:
- missing module → `SD601`
- import cycles → `SD603`

## How CLI commands use imports

`sigmadsl validate`, `sigmadsl lint`, `sigmadsl run`, and `sigmadsl profile` all:

- resolve imports deterministically starting from the provided entry path
- validate the dependency graph and reject cycles
- then process the import closure

## Minimal demo

Example pack:

```
pack_ok/
  main.sr
  lib/
    util.sr
```

Run the entry module:

```bash
sigmadsl validate pack_ok/main.sr
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules pack_ok/main.sr
```

