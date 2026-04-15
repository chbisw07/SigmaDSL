from __future__ import annotations

from pathlib import Path

import typer

from .diagnostics import Diagnostic
from .validate import validate_paths

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.callback()
def _main():
    """SigmaDSL CLI (v0.1 authoring bootstrap)."""


def _format_diag(diag: Diagnostic) -> str:
    loc = diag.location
    if loc.file:
        try:
            file_part = str(loc.file.resolve().relative_to(Path.cwd().resolve()))
        except Exception:
            file_part = str(loc.file)
    else:
        file_part = "<unknown>"
    if loc.line is not None and loc.column is not None:
        pos = f"{file_part}:{loc.line}:{loc.column}"
    elif loc.line is not None:
        pos = f"{file_part}:{loc.line}"
    else:
        pos = file_part
    return f"{pos} {diag.code} {diag.severity.value}: {diag.message}"


@app.command()
def validate(path: Path = typer.Argument(..., exists=True, readable=True)):
    """
    Validate one SigmaDSL source file (or directory of .sr files).
    """

    diags: list[Diagnostic] = validate_paths(path)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    typer.echo("OK")
