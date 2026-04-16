from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .runtime_models import Bar, UnderlyingEvent, dec, dec_str


RUNLOG_SCHEMA = "sigmadsl.runlog"
RUNLOG_SCHEMA_VERSION = "0.4-a"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RuleSource:
    path: str
    sha256: str
    text: str

    def to_dict(self) -> dict:
        return {"path": self.path, "sha256": self.sha256, "text": self.text}


@dataclass(frozen=True)
class CsvSourceMeta:
    path: str
    sha256: str
    columns: tuple[str, ...]
    row_count: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "columns": list(self.columns),
            "row_count": self.row_count,
        }


def underlying_event_to_dict(ev: UnderlyingEvent) -> dict:
    bar = ev.bar
    return {
        "symbol": ev.symbol,
        "index": ev.index,
        "bar": {
            "timestamp": bar.timestamp,
            "open": dec_str(bar.open),
            "high": dec_str(bar.high),
            "low": dec_str(bar.low),
            "close": dec_str(bar.close),
            "volume": dec_str(bar.volume),
        },
        "data_is_fresh": ev.data_is_fresh,
        "session_is_regular": ev.session_is_regular,
        "underlying_return_5m": dec_str(ev.underlying_return_5m) if ev.underlying_return_5m is not None else None,
    }


def underlying_event_from_dict(d: dict, *, file: Path | None = None) -> tuple[UnderlyingEvent | None, list[Diagnostic]]:
    diags: list[Diagnostic] = []

    try:
        symbol = str(d["symbol"])
        index = int(d["index"])
        bar_d = d["bar"]
        bar = Bar(
            timestamp=str(bar_d["timestamp"]),
            open=dec(bar_d["open"]),
            high=dec(bar_d["high"]),
            low=dec(bar_d["low"]),
            close=dec(bar_d["close"]),
            volume=dec(bar_d["volume"]),
        )
        data_is_fresh = bool(d.get("data_is_fresh", True))
        session_is_regular = bool(d.get("session_is_regular", True))
        uret = d.get("underlying_return_5m")
        underlying_return_5m = dec(uret) if uret is not None else None
    except Exception as e:
        diags.append(
            diag(
                code="SD544",
                severity=Severity.error,
                message=f"Malformed underlying event in run log: {e}",
                file=file,
            )
        )
        return None, diags

    return (
        UnderlyingEvent(
            symbol=symbol,
            index=index,
            bar=bar,
            data_is_fresh=data_is_fresh,
            session_is_regular=session_is_regular,
            underlying_return_5m=underlying_return_5m,
        ),
        [],
    )


@dataclass(frozen=True)
class RunLog:
    schema: str
    schema_version: str
    engine_version: str
    rules: tuple[RuleSource, ...]
    input_csv: CsvSourceMeta
    events: tuple[UnderlyingEvent, ...]

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "rules": {"files": [r.to_dict() for r in self.rules]},
            "input": {
                "csv": self.input_csv.to_dict(),
                "events": [underlying_event_to_dict(e) for e in self.events],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def load_runlog(path: Path) -> tuple[RunLog | None, list[Diagnostic]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, [diag(code="SD540", severity=Severity.error, message=f"Failed to read log: {e}", file=path)]

    try:
        d = json.loads(text)
    except Exception as e:
        return None, [diag(code="SD540", severity=Severity.error, message=f"Failed to parse log JSON: {e}", file=path)]

    if not isinstance(d, dict):
        return None, [diag(code="SD540", severity=Severity.error, message="Run log must be a JSON object", file=path)]

    if d.get("schema") != RUNLOG_SCHEMA:
        return None, [
            diag(
                code="SD541",
                severity=Severity.error,
                message=f"Unsupported run log schema (expected {RUNLOG_SCHEMA!r})",
                file=path,
            )
        ]

    if d.get("schema_version") != RUNLOG_SCHEMA_VERSION:
        return None, [
            diag(
                code="SD541",
                severity=Severity.error,
                message=f"Unsupported run log schema_version (expected {RUNLOG_SCHEMA_VERSION!r})",
                file=path,
            )
        ]

    try:
        engine_version = str(d["engine_version"])
        rules_files = d["rules"]["files"]
        input_csv_d = d["input"]["csv"]
        events_d = d["input"]["events"]
    except Exception as e:
        return None, [diag(code="SD542", severity=Severity.error, message=f"Missing required log fields: {e}", file=path)]

    rules: list[RuleSource] = []
    try:
        for rf in rules_files:
            rules.append(RuleSource(path=str(rf["path"]), sha256=str(rf["sha256"]), text=str(rf["text"])))
    except Exception as e:
        return None, [diag(code="SD543", severity=Severity.error, message=f"Malformed rules snapshot in log: {e}", file=path)]

    try:
        csv_meta = CsvSourceMeta(
            path=str(input_csv_d["path"]),
            sha256=str(input_csv_d["sha256"]),
            columns=tuple(str(c) for c in input_csv_d["columns"]),
            row_count=int(input_csv_d["row_count"]),
        )
    except Exception as e:
        return None, [diag(code="SD542", severity=Severity.error, message=f"Malformed input.csv section in log: {e}", file=path)]

    events: list[UnderlyingEvent] = []
    diags: list[Diagnostic] = []
    if not isinstance(events_d, list):
        return None, [diag(code="SD544", severity=Severity.error, message="input.events must be a list", file=path)]
    for ev_d in events_d:
        ev, ev_diags = underlying_event_from_dict(ev_d, file=path)
        diags.extend(ev_diags)
        if ev is not None:
            events.append(ev)
    if diags:
        return None, sorted(diags)

    return (
        RunLog(
            schema=RUNLOG_SCHEMA,
            schema_version=RUNLOG_SCHEMA_VERSION,
            engine_version=engine_version,
            rules=tuple(rules),
            input_csv=csv_meta,
            events=tuple(events),
        ),
        [],
    )


def write_runlog(path: Path, log: RunLog) -> list[Diagnostic]:
    try:
        path.write_text(log.to_json(), encoding="utf-8")
        return []
    except Exception as e:
        return [diag(code="SD540", severity=Severity.error, message=f"Failed to write log: {e}", file=path)]

