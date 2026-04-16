from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .runtime_models import Bar, UnderlyingEvent, dec


_REQUIRED_COLUMNS = ("symbol", "timestamp", "open", "high", "low", "close", "volume")
_OPTIONAL_COLUMNS = ("underlying_return_5m", "data_is_fresh", "session_is_regular")


@dataclass(frozen=True)
class CsvLoadMeta:
    columns: tuple[str, ...]
    row_count: int


def load_underlying_events_csv_with_meta(path: Path) -> tuple[list[UnderlyingEvent], CsvLoadMeta | None, list[Diagnostic]]:
    events, meta, diags = _load_underlying_events_csv_impl(path)
    return events, meta, diags


def load_underlying_events_csv(path: Path) -> tuple[list[UnderlyingEvent], list[Diagnostic]]:
    """
    Sprint 0.3-B: strict CSV loader for a minimal equity/bar input model.

    CSV requirements (v0.3-B):
    - single-symbol series only (all rows must share the same `symbol`)
    - required columns: symbol, timestamp, open, high, low, close, volume
    - optional columns: underlying_return_5m, data_is_fresh, session_is_regular

    Diagnostics are deterministic: sorted by (file, line, column, code, message).
    """

    events, _, diags = _load_underlying_events_csv_impl(path)
    return events, diags


def _load_underlying_events_csv_impl(path: Path) -> tuple[list[UnderlyingEvent], CsvLoadMeta | None, list[Diagnostic]]:
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        return [], None, [diag(code="SD520", message="CSV is missing a header row", file=path)]

    missing = [c for c in _REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        return [], None, [
            diag(
                code="SD520",
                message=f"CSV is missing required column(s): {', '.join(missing)}",
                file=path,
                severity=Severity.error,
            )
        ]

    events: list[UnderlyingEvent] = []
    diags: list[Diagnostic] = []
    first_symbol: str | None = None

    for row_i, row in enumerate(reader, start=2):  # header is line 1
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            diags.append(diag(code="SD521", message="CSV row has empty 'symbol'", file=path, line=row_i, column=1))
            continue

        if first_symbol is None:
            first_symbol = symbol
        elif symbol != first_symbol:
            diags.append(
                diag(
                    code="SD522",
                    message=(
                        "v0.3-B runner supports a single-symbol bar series only; "
                        f"expected {first_symbol!r}, got {symbol!r}"
                    ),
                    file=path,
                    line=row_i,
                    column=1,
                )
            )
            continue

        timestamp = (row.get("timestamp") or "").strip()
        if not timestamp:
            diags.append(diag(code="SD521", message="CSV row has empty 'timestamp'", file=path, line=row_i, column=1))
            continue

        try:
            bar = Bar(
                timestamp=timestamp,
                open=_dec_field(row, "open"),
                high=_dec_field(row, "high"),
                low=_dec_field(row, "low"),
                close=_dec_field(row, "close"),
                volume=_dec_field(row, "volume"),
            )
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        try:
            underlying_return_5m = _dec_optional(row, "underlying_return_5m")
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        try:
            data_is_fresh = _bool_optional(row, "data_is_fresh", default=True)
            session_is_regular = _bool_optional(row, "session_is_regular", default=True)
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        events.append(
            UnderlyingEvent(
                symbol=symbol,
                index=len(events),
                bar=bar,
                data_is_fresh=data_is_fresh,
                session_is_regular=session_is_regular,
                underlying_return_5m=underlying_return_5m,
            )
        )

    if not diags and not events:
        diags.append(diag(code="SD523", message="CSV has no data rows", file=path))

    meta = CsvLoadMeta(columns=tuple(reader.fieldnames), row_count=len(events))
    return events, meta, sorted(diags)


@dataclass(frozen=True)
class _FieldError(Exception):
    message: str


def _dec_field(row: dict[str, str | None], name: str) -> Decimal:
    raw = row.get(name)
    if raw is None:
        raise _FieldError(f"Missing CSV field: {name!r}")
    s = str(raw).strip()
    if s == "":
        raise _FieldError(f"CSV field {name!r} is empty")
    try:
        return dec(s)
    except (InvalidOperation, ValueError) as e:
        raise _FieldError(f"CSV field {name!r} is not a valid decimal: {s!r}") from e


def _dec_optional(row: dict[str, str | None], name: str) -> Decimal | None:
    raw = row.get(name)
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    try:
        return dec(s)
    except (InvalidOperation, ValueError) as e:
        raise _FieldError(f"CSV field {name!r} is not a valid decimal: {s!r}") from e


def _bool_optional(row: dict[str, str | None], name: str, *, default: bool) -> bool:
    raw = row.get(name)
    if raw is None:
        return default
    s = str(raw).strip().lower()
    if s == "":
        return default
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    raise _FieldError(f"CSV field {name!r} is not a valid bool (true/false/1/0/yes/no): {raw!r}")
