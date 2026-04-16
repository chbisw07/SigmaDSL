from __future__ import annotations

from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .decision_profiles import DecisionProfile
from .modules import load_modules_for_path, resolve_import_closure
from .profile_compliance import check_profile_compliance
from .typechecker import typecheck_source_file


def validate_paths(path: Path, *, profile: DecisionProfile = DecisionProfile.signal) -> list[Diagnostic]:
    modules, index_diags, root = load_modules_for_path(path)
    if index_diags:
        return sorted(index_diags)

    entry_paths = [path] if path.is_file() else [m.path for m in modules]
    closure, import_diags = resolve_import_closure(root=root, modules=modules, entry_paths=entry_paths)
    if import_diags:
        return sorted(import_diags)

    all_diags: list[Diagnostic] = []
    for m in closure:
        all_diags.extend(m.parse_diags)
        if m.source_file is not None and not m.parse_diags:
            all_diags.extend(typecheck_source_file(m.source_file))
            all_diags.extend(check_profile_compliance(m.source_file, profile=profile, file=m.path))
    return sorted(all_diags)
