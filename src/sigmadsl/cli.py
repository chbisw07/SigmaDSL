from __future__ import annotations

from pathlib import Path

import typer

from .diagnostics import Diagnostic
from .linting import lint_paths
from .runner import decision_jsonl_lines, explain_decision_text, run_underlying_from_csv
from .validate import validate_paths

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.callback()
def _main():
    """SigmaDSL CLI (sprint-based; v0.3 includes deterministic run + trace)."""


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


@app.command()
def lint(path: Path = typer.Argument(..., exists=True, readable=True)):
    """
    Lint SigmaDSL sources for guardrails and profile compliance.
    """

    diags: list[Diagnostic] = lint_paths(path)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    typer.echo("OK")


@app.command()
def run(
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Path to bars CSV"),
    rules: Path = typer.Option(..., "--rules", exists=True, readable=True, help="Rule file or directory"),
    format: str = typer.Option("jsonl", "--format", help="Output format: jsonl or json"),
):
    """
    Run SigmaDSL rules deterministically on a bars CSV (Sprint 0.3-B).
    """

    result, diags = run_underlying_from_csv(rules_path=rules, input_csv=input)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    assert result is not None

    fmt = format.strip().lower()
    if fmt not in ("jsonl", "json"):
        typer.echo("Invalid --format (expected 'jsonl' or 'json')", err=True)
        raise typer.Exit(code=2)

    if fmt == "jsonl":
        for line in decision_jsonl_lines(result):
            typer.echo(line.rstrip("\n"))
    else:
        # Stable full JSON output (decisions only).
        import json

        decisions = [json.loads(l) for l in decision_jsonl_lines(result)]
        typer.echo(json.dumps(decisions, sort_keys=True, indent=2))


@app.command()
def explain(
    decision_id: str = typer.Option(..., "--decision-id", help="Decision id to explain (e.g., D0003)"),
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Path to bars CSV"),
    rules: Path = typer.Option(..., "--rules", exists=True, readable=True, help="Rule file or directory"),
):
    """
    Explain a single decision by re-running evaluation and printing the emitting rule trace (Sprint 0.3-B).
    """

    result, diags = run_underlying_from_csv(rules_path=rules, input_csv=input)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    assert result is not None

    text = explain_decision_text(result, decision_id)
    if text is None:
        typer.echo(f"Decision not found: {decision_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(text.rstrip("\n"))
