from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    error = "error"
    warning = "warning"


@dataclass(frozen=True)
class DiagnosticLocation:
    file: Path | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    location: DiagnosticLocation

    def sort_key(self) -> tuple[str, int, int, str, str]:
        file_s = str(self.location.file) if self.location.file else ""
        line = self.location.line if self.location.line is not None else 0
        col = self.location.column if self.location.column is not None else 0
        return (file_s, line, col, self.code, self.message)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Diagnostic):
            return NotImplemented
        return self.sort_key() < other.sort_key()


def diag(
    *,
    code: str,
    message: str,
    file: Path | None = None,
    line: int | None = None,
    column: int | None = None,
    severity: Severity = Severity.error,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        location=DiagnosticLocation(file=file, line=line, column=column),
    )

