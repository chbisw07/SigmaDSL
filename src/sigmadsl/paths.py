from __future__ import annotations

from pathlib import Path


def discover_sr_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.sr") if p.is_file())

