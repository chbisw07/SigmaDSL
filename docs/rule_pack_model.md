# Rule pack packaging model (v0.6-B)

This page describes the **implemented** local packaging model introduced in **Sprint v0.6-B**.

Scope:
- deterministic local bundling of a rule pack (import closure) into a single artifact
- manifest + hashes for integrity verification
- `sigmadsl pack` and `sigmadsl validate --pack`

Out of scope:
- publish/install workflows
- registries, dependency download
- signing / trust infrastructure

## Artifact format

v0.6-B uses a deterministic **zip** container (stored, stable ordering).

Inside the artifact:

- `manifest.json` (pack metadata + file hashes)
- `rules/...` (bundled `.sr` source files)

## Manifest fields (v0.6-B)

`manifest.json` contains:

- `schema`: `sigmadsl.pack`
- `schema_version`: `0.6-b`
- `name`, `version`
- `compat`:
  - currently includes `dsl_spec` (e.g., `dsl_v0.6`)
- `entrypoints[]` (module names for the entry path used during packing)
- `modules[]`: `{ name, path }` mapping for each bundled module
- `files[]`: `{ path, sha256, bytes_len }` for integrity verification

## Commands

Create a pack:

```bash
sigmadsl pack path/to/entry_or_dir --out my_pack.zip --name my_rules --version 0.1.0
```

Validate a pack:

```bash
sigmadsl validate --pack my_pack.zip
```

## What packaging does (and does not do)

Does:
- captures the deterministic import closure into one artifact
- records hashes so tampering/corruption is detectable
- `sigmadsl validate --pack` runs pack integrity checks + parse/import/type validation on embedded sources

Does not:
- install anything system-wide
- download dependencies
- provide signatures/trust chains (later)
- run `sigmadsl lint` checks on packs (no `lint --pack` yet)
