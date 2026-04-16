from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .decision_profiles import DecisionProfile
from .diagnostics import Diagnostic, Severity, diag
from .modules import LoadedModule, load_modules_for_path, module_name_for_file, resolve_import_closure
from .profile_compliance import check_profile_compliance


PACK_SCHEMA = "sigmadsl.pack"
PACK_SCHEMA_VERSION = "0.6-b"
PACK_MANIFEST_PATH = "manifest.json"
PACK_RULES_DIR = "rules"

# Spec-id style compatibility marker (kept intentionally simple in v0.6-B).
CURRENT_DSL_SPEC_ID = "dsl_v0.6"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


@dataclass(frozen=True)
class PackFile:
    path: str  # inside pack (posix)
    sha256: str
    bytes_len: int

    def to_dict(self) -> dict:
        return {"path": self.path, "sha256": self.sha256, "bytes_len": self.bytes_len}


@dataclass(frozen=True)
class PackManifest:
    schema: str
    schema_version: str
    name: str
    version: str
    compat: dict
    entrypoints: tuple[str, ...]
    modules: tuple[dict, ...]  # [{name, path}]
    files: tuple[PackFile, ...]

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "name": self.name,
            "version": self.version,
            "compat": self.compat,
            "entrypoints": list(self.entrypoints),
            "modules": list(self.modules),
            "files": [f.to_dict() for f in self.files],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def create_pack(
    *,
    path: Path,
    out: Path,
    name: str,
    version: str,
) -> list[Diagnostic]:
    """
    Create a deterministic local pack artifact (v0.6-B).

    - Bundles the import closure into a single zip file.
    - Includes a manifest with hashes for integrity checking.
    """

    modules, index_diags, root = load_modules_for_path(path)
    if index_diags:
        return index_diags

    entry_paths = [path] if path.is_file() else [m.path for m in modules]
    closure, import_diags = resolve_import_closure(root=root, modules=modules, entry_paths=entry_paths)
    if import_diags:
        return import_diags

    # Packing relies on parsed import declarations to compute the closure, so we
    # refuse to pack sources with syntax errors (type/lint are left to validate/lint).
    parse_diags: list[Diagnostic] = []
    for m in closure:
        parse_diags.extend(m.parse_diags)
    if parse_diags:
        return sorted(parse_diags)

    # Build internal paths and manifest items deterministically.
    mod_items: list[dict] = []
    file_items: list[PackFile] = []
    internal_by_path: dict[Path, str] = {}

    for m in closure:
        rel = m.path.relative_to(root)
        internal = str(PurePosixPath(PACK_RULES_DIR) / PurePosixPath(rel.as_posix()))
        internal_by_path[m.path] = internal
        mod_items.append({"name": m.name, "path": internal})
        b = m.text.encode("utf-8")
        file_items.append(PackFile(path=internal, sha256=sha256_bytes(b), bytes_len=len(b)))

    # Stable ordering: by internal path.
    mod_items = sorted(mod_items, key=lambda d: d["path"])
    file_items = tuple(sorted(file_items, key=lambda f: f.path))

    entry_module_names: list[str] = []
    if path.is_file():
        mn, _ = module_name_for_file(path, root=root)
        if mn is not None:
            entry_module_names = [mn]
    else:
        entry_module_names = [m.name for m in modules]
    entry_module_names = sorted(set(entry_module_names))

    manifest = PackManifest(
        schema=PACK_SCHEMA,
        schema_version=PACK_SCHEMA_VERSION,
        name=name,
        version=version,
        compat={"dsl_spec": CURRENT_DSL_SPEC_ID},
        entrypoints=tuple(entry_module_names),
        modules=tuple(mod_items),
        files=file_items,
    )

    try:
        _write_pack_zip(out=out, manifest=manifest, closure=closure, root=root, internal_by_path=internal_by_path)
        return []
    except Exception as e:
        return [diag(code="SD630", severity=Severity.error, message=f"Failed to write pack: {e}", file=out)]


def _write_pack_zip(
    *,
    out: Path,
    manifest: PackManifest,
    closure: list[LoadedModule],
    root: Path,
    internal_by_path: dict[Path, str],
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)

    # Ensure deterministic bytes: ZIP_STORED and fixed timestamps/order.
    fixed_dt = (1980, 1, 1, 0, 0, 0)

    def write_bytes(zf: zipfile.ZipFile, arc: str, data: bytes):
        zi = zipfile.ZipInfo(filename=arc, date_time=fixed_dt)
        zi.compress_type = zipfile.ZIP_STORED
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, data)

    with zipfile.ZipFile(out, "w") as zf:
        write_bytes(zf, PACK_MANIFEST_PATH, manifest.to_json().encode("utf-8"))

        # Stable file order by internal path.
        for m in sorted(closure, key=lambda mm: internal_by_path[mm.path]):
            arc = internal_by_path[m.path]
            write_bytes(zf, arc, m.text.encode("utf-8"))


def validate_pack(path: Path, *, profile: DecisionProfile = DecisionProfile.signal) -> list[Diagnostic]:
    """
    Validate a pack artifact deterministically (v0.6-B).

    Checks:
    - manifest schema/version
    - file presence and sha256 integrity
    - module mapping consistency
    - import graph validity (missing targets / cycles)
    - type checking of embedded sources
    """

    try:
        with zipfile.ZipFile(path, "r") as zf:
            return _validate_pack_zip(path=path, zf=zf, profile=profile)
    except zipfile.BadZipFile:
        return [diag(code="SD631", severity=Severity.error, message="Pack is not a valid zip file", file=path)]
    except Exception as e:
        return [diag(code="SD631", severity=Severity.error, message=f"Failed to read pack: {e}", file=path)]


def _validate_pack_zip(*, path: Path, zf: zipfile.ZipFile, profile: DecisionProfile) -> list[Diagnostic]:
    diags: list[Diagnostic] = []

    try:
        manifest_text = zf.read(PACK_MANIFEST_PATH).decode("utf-8")
    except KeyError:
        return [diag(code="SD632", severity=Severity.error, message="Missing manifest.json in pack", file=path)]
    except Exception as e:
        return [diag(code="SD632", severity=Severity.error, message=f"Failed to read manifest: {e}", file=path)]

    try:
        md = json.loads(manifest_text)
    except Exception as e:
        return [diag(code="SD632", severity=Severity.error, message=f"Failed to parse manifest JSON: {e}", file=path)]

    if not isinstance(md, dict):
        return [diag(code="SD632", severity=Severity.error, message="Manifest must be a JSON object", file=path)]

    if md.get("schema") != PACK_SCHEMA:
        return [diag(code="SD632", severity=Severity.error, message="Unsupported pack schema", file=path)]
    if md.get("schema_version") != PACK_SCHEMA_VERSION:
        return [
            diag(
                code="SD632",
                severity=Severity.error,
                message=f"Unsupported pack schema_version (expected {PACK_SCHEMA_VERSION!r})",
                file=path,
            )
        ]

    compat = md.get("compat") or {}
    dsl_spec = compat.get("dsl_spec")
    if isinstance(dsl_spec, str):
        if _dsl_spec_tuple(dsl_spec) is None:
            diags.append(
                diag(code="SD633", severity=Severity.error, message=f"Invalid compat.dsl_spec: {dsl_spec!r}", file=path)
            )
        else:
            want = _dsl_spec_tuple(CURRENT_DSL_SPEC_ID)
            got = _dsl_spec_tuple(dsl_spec)
            if want is not None and got is not None and got > want:
                diags.append(
                    diag(
                        code="SD633",
                        severity=Severity.error,
                        message=f"Incompatible pack (requires {dsl_spec!r}, current {CURRENT_DSL_SPEC_ID!r})",
                        file=path,
                    )
                )
    else:
        diags.append(diag(code="SD633", severity=Severity.error, message="Missing compat.dsl_spec", file=path))

    files = md.get("files")
    modules = md.get("modules")
    entrypoints = md.get("entrypoints")

    if not isinstance(files, list) or not isinstance(modules, list) or not isinstance(entrypoints, list):
        diags.append(diag(code="SD632", severity=Severity.error, message="Malformed manifest fields", file=path))
        return sorted(diags)

    # Verify files/hashes.
    expected: dict[str, str] = {}
    for f in files:
        try:
            p = str(f["path"])
            h = str(f["sha256"])
        except Exception:
            diags.append(diag(code="SD632", severity=Severity.error, message="Malformed files[] entry", file=path))
            continue
        if not _is_safe_pack_path(p):
            diags.append(diag(code="SD632", severity=Severity.error, message=f"Unsafe file path in manifest: {p!r}", file=path))
            continue
        expected[p] = h

    for p, h in sorted(expected.items()):
        try:
            data = zf.read(p)
        except KeyError:
            diags.append(diag(code="SD634", severity=Severity.error, message=f"Missing file in pack: {p!r}", file=path))
            continue
        got = sha256_bytes(data)
        if got != h:
            diags.append(
                diag(
                    code="SD634",
                    severity=Severity.error,
                    message=f"Hash mismatch for {p!r} (expected {h}, got {got})",
                    file=path,
                )
            )

    # Verify module mapping consistency and parse modules.
    # Build LoadedModule list from the zip contents.
    loaded: list[LoadedModule] = []
    by_name: dict[str, LoadedModule] = {}
    root = Path(PACK_RULES_DIR)

    for m in modules:
        try:
            name = str(m["name"])
            mp = str(m["path"])
        except Exception:
            diags.append(diag(code="SD632", severity=Severity.error, message="Malformed modules[] entry", file=path))
            continue
        if mp not in expected:
            diags.append(diag(code="SD632", severity=Severity.error, message=f"Module path not in files list: {mp!r}", file=path))
            continue
        if not _is_safe_pack_path(mp):
            diags.append(diag(code="SD632", severity=Severity.error, message=f"Unsafe module path: {mp!r}", file=path))
            continue
        p_obj = Path(mp)
        # Verify name matches mapping rule.
        derived, _ = module_name_for_file(p_obj, root=root)
        if derived is not None and derived != name:
            diags.append(
                diag(
                    code="SD635",
                    severity=Severity.error,
                    message=f"Module mapping mismatch for {mp!r} (manifest name {name!r}, derived {derived!r})",
                    file=path,
                )
            )
            continue
        text = zf.read(mp).decode("utf-8")
        sf, parse_diags = parse_source(text, file=p_obj)  # type: ignore[name-defined]
        loaded_mod = LoadedModule(name=name, path=p_obj, text=text, source_file=sf, parse_diags=tuple(parse_diags))
        loaded.append(loaded_mod)
        by_name[name] = loaded_mod

    if diags:
        return sorted(diags)

    # Ensure entrypoints exist.
    entry_paths: list[Path] = []
    for ep in entrypoints:
        if not isinstance(ep, str) or ep not in by_name:
            diags.append(diag(code="SD632", severity=Severity.error, message=f"Unknown entrypoint: {ep!r}", file=path))
            continue
        entry_paths.append(by_name[ep].path)

    if diags:
        return sorted(diags)

    # Resolve import graph and detect cycles/missing imports based on embedded sources.
    closure, import_diags = resolve_import_closure(root=root, modules=loaded, entry_paths=entry_paths)
    if import_diags:
        # Attach the pack file as the diagnostic "file" for stable UX.
        return [
            _wrap_diag_for_pack(pack_path=path, inner_path=d.location.file, inner=d)
            for d in import_diags
        ]

    # Finally ensure the closure parses (parse errors are pack-invalid).
    parse_diags: list[Diagnostic] = []
    for m in closure:
        parse_diags.extend(m.parse_diags)
    if parse_diags:
        return [
            _wrap_diag_for_pack(pack_path=path, inner_path=d.location.file, inner=d)
            for d in sorted(parse_diags)
        ]

    # Type check (validate semantics) using the embedded sources.
    from .typechecker import typecheck_source_file

    type_diags: list[Diagnostic] = []
    for m in closure:
        if m.source_file is None:
            continue
        type_diags.extend(typecheck_source_file(m.source_file))
        type_diags.extend(check_profile_compliance(m.source_file, profile=profile, file=m.path))
    if type_diags:
        return [_wrap_diag_for_pack(pack_path=path, inner_path=d.location.file, inner=d) for d in sorted(type_diags)]

    return []


def _dsl_spec_tuple(spec: str) -> tuple[int, int] | None:
    # Accept `dsl_v0.6` or `dsl_v0.6.md`-like.
    s = spec.strip()
    if s.endswith(".md"):
        s = s[:-3]
    if not s.startswith("dsl_v"):
        return None
    try:
        rest = s[len("dsl_v") :]
        major_s, minor_s = rest.split(".", 1)
        return int(major_s), int(minor_s)
    except Exception:
        return None


def _is_safe_pack_path(p: str) -> bool:
    pp = PurePosixPath(p)
    if pp.is_absolute():
        return False
    if any(part == ".." for part in pp.parts):
        return False
    return True


def _wrap_diag_for_pack(*, pack_path: Path, inner_path: Path | None, inner: Diagnostic) -> Diagnostic:
    """
    Re-wrap an inner diagnostic so `sigmadsl validate --pack` points at the pack file,
    while still preserving which embedded file triggered the issue.
    """

    inner_s = ""
    if inner_path is not None:
        try:
            inner_s = inner_path.as_posix()
        except Exception:
            inner_s = str(inner_path)

    msg = inner.message if not inner_s else f"[{inner_s}] {inner.message}"
    return diag(
        code=inner.code,
        severity=inner.severity,
        message=msg,
        file=pack_path,
        line=inner.location.line,
        column=inner.location.column,
    )


# Local import to avoid cyclic imports in module graph.
from .parser import parse_source  # noqa: E402
