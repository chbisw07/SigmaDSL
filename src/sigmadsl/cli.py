from __future__ import annotations

from pathlib import Path

import typer

from .diagnostics import Diagnostic
from .diffing import diff_run_logs
from .linting import lint_paths
from .explain import explain_decision, explain_rule_at_event
from .runner import (
    decision_jsonl_lines,
    replay_from_log,
    run_underlying_from_csv_with_log,
)
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
    log_out: Path | None = typer.Option(None, "--log-out", help="Write a replayable run log (Sprint 0.4-A)"),
):
    """
    Run SigmaDSL rules deterministically on a bars CSV (Sprint 0.3-B; logs added in 0.4-A).
    """

    result, diags = run_underlying_from_csv_with_log(rules_path=rules, input_csv=input, log_out=log_out)
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
    decision_id: str | None = typer.Option(None, "--decision-id", help="Decision id to explain (e.g., D0003)"),
    rule: str | None = typer.Option(None, "--rule", help="Rule name to explain"),
    event_index: int | None = typer.Option(None, "--event-index", help="Event index (0-based) for --rule mode"),
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Path to bars CSV"),
    rules: Path = typer.Option(..., "--rules", exists=True, readable=True, help="Rule file or directory"),
):
    """
    Explain deterministic evaluation outcomes (Sprint 0.4-B).

    Modes:
    - `--decision-id`: explain why that decision fired
    - `--rule` + `--event-index`: explain why a rule fired or did not fire at a specific event
    """

    result, diags = run_underlying_from_csv_with_log(rules_path=rules, input_csv=input, log_out=None)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    assert result is not None

    if decision_id is not None:
        text = explain_decision(result, decision_id)
        if text is None:
            typer.echo(f"Decision not found: {decision_id}", err=True)
            raise typer.Exit(code=1)
        typer.echo(text.rstrip("\n"))
        return

    if rule is not None and event_index is not None:
        text = explain_rule_at_event(result, rule_name=rule, event_index=event_index)
        if text is None:
            typer.echo("Explain failed: rule or event not found", err=True)
            raise typer.Exit(code=1)
        typer.echo(text.rstrip("\n"))
        return

    typer.echo("Explain requires --decision-id or (--rule and --event-index)", err=True)
    raise typer.Exit(code=2)


@app.command()
def replay(
    log: Path = typer.Option(..., "--log", exists=True, readable=True, help="Path to a run log JSON file"),
    format: str = typer.Option("jsonl", "--format", help="Output format: jsonl or json"),
):
    """
    Replay a recorded run log deterministically (Sprint 0.4-A).
    """

    result, diags = replay_from_log(log_path=log)
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
        import json

        decisions = [json.loads(l) for l in decision_jsonl_lines(result)]
        typer.echo(json.dumps(decisions, sort_keys=True, indent=2))


@app.command()
def diff(
    log_a: Path = typer.Argument(..., exists=True, readable=True),
    log_b: Path = typer.Argument(..., exists=True, readable=True),
):
    """
    Compare two run logs deterministically (Sprint 0.4-B).

    Exit code: 0 if equal, 1 if different, 2 on errors.
    """

    summary, diags = diff_run_logs(log_a, log_b)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=2)
    assert summary is not None
    typer.echo(summary.to_text().rstrip("\n"))
    raise typer.Exit(code=0 if summary.equal else 1)
