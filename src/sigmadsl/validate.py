from __future__ import annotations

from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .parser import parse_source


def _discover_sr_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files = sorted(p for p in path.rglob("*.sr") if p.is_file())
    return files


def validate_paths(path: Path) -> list[Diagnostic]:
    files = _discover_sr_files(path)
    if not files:
        return [diag(code="SD000", message="No .sr files found", file=path, severity=Severity.error)]

    all_diags: list[Diagnostic] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        _, diags = parse_source(text, file=file)
        all_diags.extend(diags)
    return sorted(all_diags)
