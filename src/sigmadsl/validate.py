from __future__ import annotations

from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .paths import discover_sr_files
from .parser import parse_source
from .typechecker import typecheck_source_file


def validate_paths(path: Path) -> list[Diagnostic]:
    files = discover_sr_files(path)
    if not files:
        return [diag(code="SD000", message="No .sr files found", file=path, severity=Severity.error)]

    all_diags: list[Diagnostic] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        source_file, parse_diags = parse_source(text, file=file)
        all_diags.extend(parse_diags)
        if source_file is not None and not parse_diags:
            all_diags.extend(typecheck_source_file(source_file))
    return sorted(all_diags)
