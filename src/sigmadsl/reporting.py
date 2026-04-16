from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag


REPORT_SCHEMA = "sigmadsl.report"
REPORT_SCHEMA_VERSION = "1.0-c"


def _timestamp_to_day(ts: str) -> str | None:
    # Fast-path for the engine's current timestamp shape.
    # Examples: 2026-01-01T09:15:00, 2026-01-01T09:15:00+05:30, 2026-01-01T09:15:00Z
    if len(ts) >= 10 and ts[4:5] == "-" and ts[7:8] == "-":
        return ts[:10]

    # Conservative fallback for any future timestamp variant.
    try:
        from datetime import datetime

        iso = ts
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        return datetime.fromisoformat(iso).date().isoformat()
    except Exception:
        return None


@dataclass(frozen=True)
class ReportRow:
    day: str
    symbol: str
    rule_name: str
    total: int
    allowed: int
    blocked: int
    by_kind: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "symbol": self.symbol,
            "rule_name": self.rule_name,
            "total": self.total,
            "allowed": self.allowed,
            "blocked": self.blocked,
            "by_kind": {k: self.by_kind[k] for k in sorted(self.by_kind)},
        }


@dataclass(frozen=True)
class ReportSummary:
    total: int
    allowed: int
    blocked: int
    by_kind: dict[str, int]
    by_profile: dict[str, int]
    rows: tuple[ReportRow, ...]

    def to_dict(self) -> dict:
        return {
            "schema": REPORT_SCHEMA,
            "schema_version": REPORT_SCHEMA_VERSION,
            "totals": {
                "total": self.total,
                "allowed": self.allowed,
                "blocked": self.blocked,
                "by_kind": {k: self.by_kind[k] for k in sorted(self.by_kind)},
                "by_profile": {k: self.by_profile[k] for k in sorted(self.by_profile)},
            },
            "by_day_symbol_rule": [r.to_dict() for r in self.rows],
        }

    def to_text(self) -> str:
        lines: list[str] = []
        lines.append("SigmaDSL report\n")
        lines.append(f"- total: {self.total}\n")
        lines.append(f"- allowed: {self.allowed}\n")
        lines.append(f"- blocked: {self.blocked}\n")
        lines.append(f"- by_kind: {json.dumps({k: self.by_kind[k] for k in sorted(self.by_kind)})}\n")
        lines.append(f"- by_profile: {json.dumps({k: self.by_profile[k] for k in sorted(self.by_profile)})}\n")
        lines.append("\n")
        lines.append("By day / symbol / rule\n")
        for r in self.rows:
            kinds = json.dumps({k: r.by_kind[k] for k in sorted(r.by_kind)})
            lines.append(
                f"- {r.day} {r.symbol} {r.rule_name}: total={r.total} allowed={r.allowed} blocked={r.blocked} by_kind={kinds}\n"
            )
        return "".join(lines)


def load_decision_dicts_jsonl(path: Path) -> tuple[list[dict], list[Diagnostic]]:
    text = path.read_text(encoding="utf-8")
    diags: list[Diagnostic] = []
    out: list[dict] = []

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            diags.append(
                diag(
                    code="SD610",
                    severity=Severity.error,
                    message="Invalid JSONL: line is not valid JSON",
                    file=path,
                    line=i,
                    column=1,
                )
            )
            continue
        if not isinstance(obj, dict):
            diags.append(
                diag(
                    code="SD610",
                    severity=Severity.error,
                    message="Invalid JSONL: each line must be a JSON object",
                    file=path,
                    line=i,
                    column=1,
                )
            )
            continue
        out.append(obj)

    return out, sorted(diags)


def aggregate_report_from_decision_dicts(decisions: list[dict], *, source: Path | None = None) -> tuple[ReportSummary | None, list[Diagnostic]]:
    diags: list[Diagnostic] = []

    total = 0
    allowed = 0
    blocked = 0
    by_kind: dict[str, int] = {}
    by_profile: dict[str, int] = {}

    # key: (day, symbol, rule_name)
    groups: dict[tuple[str, str, str], dict] = {}

    for idx, d in enumerate(decisions):
        def _err(msg: str) -> None:
            diags.append(
                diag(
                    code="SD611",
                    severity=Severity.error,
                    message=msg,
                    file=source,
                    line=idx + 1,
                    column=1,
                )
            )

        kind = d.get("kind")
        profile = d.get("profile")
        rule_name = d.get("rule_name")
        symbol = d.get("symbol")
        timestamp = d.get("timestamp")
        enforcement = d.get("enforcement")

        if not isinstance(kind, str):
            _err("Decision record missing/invalid 'kind'")
            continue
        if not isinstance(profile, str):
            _err("Decision record missing/invalid 'profile'")
            continue
        if not isinstance(rule_name, str):
            _err("Decision record missing/invalid 'rule_name'")
            continue
        if not isinstance(symbol, str):
            _err("Decision record missing/invalid 'symbol'")
            continue
        if not isinstance(timestamp, str):
            _err("Decision record missing/invalid 'timestamp'")
            continue

        status = "allowed"
        if isinstance(enforcement, dict):
            s = enforcement.get("status")
            if isinstance(s, str):
                status = s

        day = _timestamp_to_day(timestamp)
        if day is None:
            _err("Decision record has unsupported 'timestamp' format (cannot compute day)")
            continue

        total += 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_profile[profile] = by_profile.get(profile, 0) + 1
        if status == "blocked":
            blocked += 1
        else:
            allowed += 1

        k = (day, symbol, rule_name)
        g = groups.get(k)
        if g is None:
            g = {"total": 0, "allowed": 0, "blocked": 0, "by_kind": {}}
            groups[k] = g
        g["total"] += 1
        if status == "blocked":
            g["blocked"] += 1
        else:
            g["allowed"] += 1
        bk: dict[str, int] = g["by_kind"]
        bk[kind] = bk.get(kind, 0) + 1

    if diags:
        return None, sorted(diags)

    rows: list[ReportRow] = []
    for (day, symbol, rule_name), g in sorted(groups.items()):
        rows.append(
            ReportRow(
                day=day,
                symbol=symbol,
                rule_name=rule_name,
                total=int(g["total"]),
                allowed=int(g["allowed"]),
                blocked=int(g["blocked"]),
                by_kind=dict(g["by_kind"]),
            )
        )

    return (
        ReportSummary(
            total=total,
            allowed=allowed,
            blocked=blocked,
            by_kind=by_kind,
            by_profile=by_profile,
            rows=tuple(rows),
        ),
        [],
    )

