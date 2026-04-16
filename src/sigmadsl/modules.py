from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ast
from .diagnostics import Diagnostic, Severity, diag
from .parser import parse_source
from .paths import discover_sr_files


@dataclass(frozen=True)
class LoadedModule:
    name: str
    path: Path
    text: str
    source_file: ast.SourceFile | None
    parse_diags: tuple[Diagnostic, ...]


def load_modules_for_path(path: Path) -> tuple[list[LoadedModule], list[Diagnostic], Path]:
    """
    Load a deterministic module index and parse modules for a file or directory input.

    Returns:
    - modules: all discovered modules under the pack root (not filtered by entry reachability)
    - diags: index-level errors (duplicate module name mapping, path issues)
    - root: chosen pack root
    """

    if path.is_file():
        root = path.parent
    else:
        root = path

    files = discover_sr_files(root)
    if not files:
        return [], [diag(code="SD000", message="No .sr files found", file=path, severity=Severity.error)], root

    index_diags: list[Diagnostic] = []
    by_name: dict[str, Path] = {}
    modules: list[LoadedModule] = []

    for f in files:
        name, name_diags = module_name_for_file(f, root=root)
        index_diags.extend(name_diags)
        if name is None:
            continue

        if name in by_name and by_name[name] != f:
            index_diags.append(
                diag(
                    code="SD602",
                    severity=Severity.error,
                    message=f"Duplicate module name mapping for {name!r}: {str(by_name[name])!r} and {str(f)!r}",
                    file=f,
                    line=1,
                    column=1,
                )
            )
            continue
        by_name[name] = f

    if index_diags:
        # Still parse what we can; callers may want diagnostics from parsed files too.
        pass

    for name in sorted(by_name.keys()):
        f = by_name[name]
        text = f.read_text(encoding="utf-8")
        sf, parse_diags = parse_source(text, file=f)
        modules.append(
            LoadedModule(
                name=name,
                path=f,
                text=text,
                source_file=sf,
                parse_diags=tuple(parse_diags),
            )
        )

    return modules, sorted(index_diags), root


def resolve_import_closure(
    *,
    root: Path,
    modules: list[LoadedModule],
    entry_paths: list[Path],
) -> tuple[list[LoadedModule], list[Diagnostic]]:
    """
    Resolve the import closure starting from entry files under the given pack root.

    v0.6-A semantics:
    - `import foo.bar` resolves to a module named `foo.bar`
    - module names map deterministically from file paths rooted at `root`
    - cycles are rejected
    """

    by_name = {m.name: m for m in modules}
    by_path = {m.path: m for m in modules}

    entry_modules: list[str] = []
    diags: list[Diagnostic] = []

    for p in entry_paths:
        try:
            m = by_path[p]
        except KeyError:
            diags.append(
                diag(
                    code="SD600",
                    severity=Severity.error,
                    message="Entry path is not a discovered module under the pack root",
                    file=p,
                    line=1,
                    column=1,
                )
            )
            continue
        entry_modules.append(m.name)

    entry_modules = sorted(set(entry_modules))

    # Build adjacency list only for modules that parsed cleanly.
    deps: dict[str, list[str]] = {}
    for m in modules:
        if m.source_file is None or m.parse_diags:
            continue
        deps[m.name] = sorted(d.module for d in m.source_file.imports)

    # Validate imports exist.
    for m in modules:
        if m.source_file is None or m.parse_diags:
            continue
        for imp in m.source_file.imports:
            if imp.module not in by_name:
                diags.append(
                    diag(
                        code="SD601",
                        severity=Severity.error,
                        message=f"Import target not found: {imp.module!r}",
                        file=m.path,
                        line=imp.span.line,
                        column=imp.span.column,
                    )
                )

    if diags:
        return [], sorted(diags)

    ordered: list[str] = []
    state: dict[str, int] = {}  # 0=unseen,1=visiting,2=done
    stack: list[str] = []

    def dfs(name: str):
        st = state.get(name, 0)
        if st == 2:
            return
        if st == 1:
            # Cycle detected; report stable cycle path.
            if name in stack:
                i = stack.index(name)
                cycle = stack[i:] + [name]
            else:
                cycle = stack + [name]
            diags.append(
                diag(
                    code="SD603",
                    severity=Severity.error,
                    message="Import cycle detected: " + " -> ".join(cycle),
                    file=by_name[name].path,
                    line=1,
                    column=1,
                )
            )
            return
        state[name] = 1
        stack.append(name)
        for dep in deps.get(name, []):
            # Missing modules already validated above.
            dfs(dep)
        stack.pop()
        state[name] = 2
        ordered.append(name)

    for entry in entry_modules:
        dfs(entry)

    if diags:
        return [], sorted(diags)

    out = [by_name[n] for n in ordered]
    return out, []


def module_name_for_file(path: Path, *, root: Path) -> tuple[str | None, list[Diagnostic]]:
    """
    Deterministic mapping:
    - `<root>/foo/bar.sr` => `foo.bar`
    - `<root>/foo/__init__.sr` => `foo`
    - `<root>/__init__.sr` => `__root__` (not importable; usable as an entry module)
    """

    diags: list[Diagnostic] = []
    try:
        rel = path.relative_to(root)
    except Exception:
        return None, [
            diag(
                code="SD600",
                severity=Severity.error,
                message="Module file is not under the pack root",
                file=path,
                line=1,
                column=1,
            )
        ]

    if rel.suffix != ".sr":
        return None, []

    parts = list(rel.parts)
    if not parts:
        return None, []

    stem = Path(parts[-1]).stem
    if stem == "__init__":
        parts = parts[:-1]
        if not parts:
            return "__root__", []
        return ".".join(parts), []

    parts[-1] = stem
    return ".".join(parts), []

