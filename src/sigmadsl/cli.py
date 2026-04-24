from __future__ import annotations

from pathlib import Path

import typer

from .decision_profiles import DecisionProfile, parse_profile
from .diagnostics import Diagnostic
from .diffing import diff_run_logs
from .linting import lint_paths_with_profile
from .profile import profile_paths
from .packaging import create_pack, validate_pack
from .explain import explain_decision, explain_rule_at_event
from .reporting import aggregate_report_from_decision_dicts, load_decision_dicts_jsonl
from .runner import (
    decision_jsonl_lines,
    replay_from_log,
    run_option_from_csv_with_log,
    run_underlying_from_csv_with_log,
)
from .validate import validate_paths

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.callback()
def _main():
    """SigmaDSL CLI (sprint-based; v1.0 adds profiles + stable decision schema)."""


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
def validate(
    path: Path | None = typer.Argument(None),
    pack: Path | None = typer.Option(None, "--pack", exists=True, readable=True, help="Validate a packaged rule pack"),
    profile: str = typer.Option("signal", "--profile", help="Decision profile: signal, intent, or risk"),
):
    """
    Validate one SigmaDSL source file (or directory of .sr files).
    """

    if (path is None and pack is None) or (path is not None and pack is not None):
        typer.echo("validate requires either a path argument or --pack", err=True)
        raise typer.Exit(code=2)

    p = parse_profile(profile)
    if p is None:
        typer.echo("Invalid --profile (expected 'signal', 'intent', or 'risk')", err=True)
        raise typer.Exit(code=2)

    if pack is not None:
        diags = validate_pack(pack, profile=p)
    else:
        assert path is not None
        if not path.exists() or not path.is_dir() and not path.is_file():
            typer.echo("Invalid path", err=True)
            raise typer.Exit(code=2)
        diags = validate_paths(path, profile=p)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    typer.echo("OK")


@app.command()
def lint(
    path: Path = typer.Argument(..., exists=True, readable=True),
    profile: str = typer.Option("signal", "--profile", help="Decision profile: signal, intent, or risk"),
):
    """
    Lint SigmaDSL sources for guardrails and profile compliance.
    """

    p = parse_profile(profile)
    if p is None:
        typer.echo("Invalid --profile (expected 'signal', 'intent', or 'risk')", err=True)
        raise typer.Exit(code=2)

    diags: list[Diagnostic] = lint_paths_with_profile(path, profile=p)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    typer.echo("OK")


@app.command()
def run(
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Path to input CSV"),
    rules: Path = typer.Option(..., "--rules", exists=True, readable=True, help="Rule file or directory"),
    context: str = typer.Option("underlying", "--context", help="Input context: underlying or option"),
    contract_id: str | None = typer.Option(
        None,
        "--contract-id",
        help="Canonical option contract id (required if option CSV has multiple contracts)",
    ),
    profile: str = typer.Option("signal", "--profile", help="Decision profile: signal, intent, or risk"),
    risk_rules: Path | None = typer.Option(
        None, "--risk-rules", exists=True, readable=True, help="Optional risk rule pack (applied as a separate phase)"
    ),
    format: str = typer.Option("jsonl", "--format", help="Output format: jsonl or json"),
    log_out: Path | None = typer.Option(None, "--log-out", help="Write a replayable run log (Sprint 0.4-A)"),
):
    """
    Run SigmaDSL rules deterministically on a CSV input (bars or option snapshots).

    - `--context underlying`: bars CSV (Sprint 0.3-B; logs added in 0.4-A)
    - `--context option`: option snapshot CSV (Sprint v1.1-B)
    """

    p = parse_profile(profile)
    if p is None:
        typer.echo("Invalid --profile (expected 'signal', 'intent', or 'risk')", err=True)
        raise typer.Exit(code=2)

    ctx = context.strip().lower()
    if ctx not in ("underlying", "option"):
        typer.echo("Invalid --context (expected 'underlying' or 'option')", err=True)
        raise typer.Exit(code=2)
    if ctx == "underlying" and contract_id is not None:
        typer.echo("--contract-id is only valid with --context option", err=True)
        raise typer.Exit(code=2)

    if ctx == "underlying":
        result, diags = run_underlying_from_csv_with_log(
            rules_path=rules, input_csv=input, profile=p, risk_rules_path=risk_rules, log_out=log_out
        )
    else:
        result, diags = run_option_from_csv_with_log(
            rules_path=rules,
            input_csv=input,
            profile=p,
            risk_rules_path=risk_rules,
            contract_id=contract_id,
            log_out=log_out,
        )
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
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Path to input CSV"),
    rules: Path = typer.Option(..., "--rules", exists=True, readable=True, help="Rule file or directory"),
    context: str = typer.Option("underlying", "--context", help="Input context: underlying or option"),
    contract_id: str | None = typer.Option(
        None,
        "--contract-id",
        help="Canonical option contract id (required if option CSV has multiple contracts)",
    ),
    profile: str = typer.Option("signal", "--profile", help="Decision profile: signal, intent, or risk"),
    risk_rules: Path | None = typer.Option(
        None, "--risk-rules", exists=True, readable=True, help="Optional risk rule pack (applied as a separate phase)"
    ),
):
    """
    Explain deterministic evaluation outcomes (Sprint 0.4-B).

    Modes:
    - `--decision-id`: explain why that decision fired
    - `--rule` + `--event-index`: explain why a rule fired or did not fire at a specific event
    """

    p = parse_profile(profile)
    if p is None:
        typer.echo("Invalid --profile (expected 'signal', 'intent', or 'risk')", err=True)
        raise typer.Exit(code=2)

    ctx = context.strip().lower()
    if ctx not in ("underlying", "option"):
        typer.echo("Invalid --context (expected 'underlying' or 'option')", err=True)
        raise typer.Exit(code=2)
    if ctx == "underlying" and contract_id is not None:
        typer.echo("--contract-id is only valid with --context option", err=True)
        raise typer.Exit(code=2)

    if ctx == "underlying":
        result, diags = run_underlying_from_csv_with_log(
            rules_path=rules, input_csv=input, profile=p, risk_rules_path=risk_rules, log_out=None
        )
    else:
        result, diags = run_option_from_csv_with_log(
            rules_path=rules,
            input_csv=input,
            profile=p,
            risk_rules_path=risk_rules,
            contract_id=contract_id,
            log_out=None,
        )
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


@app.command()
def profile(
    path: Path = typer.Argument(..., exists=True, readable=True),
    format: str = typer.Option("json", "--format", help="Output format: json or text"),
):
    """
    Summarize which indicators/functions/verbs a rule pack uses (Sprint 0.5-B).
    """

    summary, diags = profile_paths(path)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    assert summary is not None

    fmt = format.strip().lower()
    if fmt not in ("json", "text"):
        typer.echo("Invalid --format (expected 'json' or 'text')", err=True)
        raise typer.Exit(code=2)

    if fmt == "json":
        typer.echo(summary.to_json().rstrip("\n"))
        return

    # text (stable, minimal)
    o = summary.to_dict()
    typer.echo("Profile")
    typer.echo(f"- files: {len(o['files'])}")
    typer.echo(f"- rule_count: {o['rule_count']}")
    typer.echo(f"- contexts: {', '.join(o['contexts']) or '<none>'}")
    typer.echo(f"- verbs: {', '.join(o['verbs']) or '<none>'}")
    typer.echo(f"- functions: {', '.join(o['functions']) or '<none>'}")
    inds = o["indicators"]
    typer.echo(f"- indicator_registry_version: {inds['registry_version']}")
    typer.echo(f"- indicators_referenced: {', '.join(inds['referenced']) or '<none>'}")


@app.command()
def report(
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="Decision JSONL output from run/replay"),
    format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """
    Aggregate outcomes per rule / symbol / day (Sprint v1.0-C).
    """

    decisions, diags = load_decision_dicts_jsonl(input)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=2)

    summary, diags = aggregate_report_from_decision_dicts(decisions, source=input)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=2)
    assert summary is not None

    fmt = format.strip().lower()
    if fmt not in ("text", "json"):
        typer.echo("Invalid --format (expected 'text' or 'json')", err=True)
        raise typer.Exit(code=2)

    if fmt == "json":
        import json

        typer.echo(json.dumps(summary.to_dict(), sort_keys=True, indent=2))
    else:
        typer.echo(summary.to_text().rstrip("\n"))


@app.command()
def pack(
    path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(..., "--out", help="Output pack file path"),
    name: str | None = typer.Option(None, "--name", help="Pack name (default: derived from path)"),
    version: str = typer.Option("0.0.0", "--version", help="Pack version string"),
):
    """
    Package a rule pack into a deterministic local bundle (Sprint 0.6-B).
    """

    pack_name = name or path.stem
    diags = create_pack(path=path, out=out, name=pack_name, version=version)
    if diags:
        for d in diags:
            typer.echo(_format_diag(d))
        raise typer.Exit(code=1)
    typer.echo(f"PACKED {pack_name}@{version} -> {out}")
