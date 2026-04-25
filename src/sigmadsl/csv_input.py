from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .options_contracts import parse_option_contract_id, parse_option_right
from .options_runtime import OptionEvent
from .options_snapshots import check_option_snapshot_usable, parse_option_snapshot_dict
from .options_selection import OptionSelectionCandidate, OptionSelectionRequest, select_contract_id
from .runtime_models import Bar, UnderlyingEvent, dec


_REQUIRED_COLUMNS = ("symbol", "timestamp", "open", "high", "low", "close", "volume")
_OPTIONAL_COLUMNS = ("underlying_return_5m", "data_is_fresh", "session_is_regular")


# v1.1-B: option snapshot CSV
_OPT_REQUIRED_COLUMNS = ("contract_id", "timestamp")
_OPT_OPTIONAL_COLUMNS = (
    "venue",
    "underlying",
    "expiry",
    "strike",
    "right",
    "lot",
    "bid",
    "ask",
    "last",
    "close",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
    "open_interest",
    "volume",
    "underlying_price",
    "underlying_return_5m",
    "data_is_fresh",
    "session_is_regular",
    "quality_flags",
)


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


def load_option_events_csv_with_meta(
    path: Path, *, contract_id: str | None = None
) -> tuple[list[OptionEvent], CsvLoadMeta | None, list[Diagnostic]]:
    events, meta, diags = _load_option_events_csv_impl(path, contract_id=contract_id)
    return events, meta, diags


def select_option_contract_id_from_csv(
    path: Path, *, req: OptionSelectionRequest
) -> tuple[str | None, list[Diagnostic]]:
    """
    Sprint v1.1-C: deterministically select a single contract_id from an option snapshot CSV.

    Selection is based on the *earliest timestamp* present in the CSV (lexicographic min).
    Candidate rows are the usable snapshot rows at that timestamp, one per contract_id.
    """

    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        return None, [diag(code="SD526", message="Option CSV is missing a header row", file=path)]

    missing = [c for c in _OPT_REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        return None, [
            diag(
                code="SD526",
                message=f"Option CSV is missing required column(s): {', '.join(missing)}",
                file=path,
                severity=Severity.error,
            )
        ]

    rows = list(reader)
    if not rows:
        return None, [diag(code="SD523", message="CSV has no data rows", file=path)]

    timestamps = sorted({(row.get("timestamp") or "").strip() for row in rows if (row.get("timestamp") or "").strip()})
    if not timestamps:
        return None, [
            diag(code="SD720", severity=Severity.error, message="Option CSV has no valid timestamp rows", file=path, line=1, column=1)
        ]
    selection_ts = min(timestamps)

    # Collect at most one candidate row per contract id at the selection timestamp.
    per_contract: dict[str, tuple[dict, int]] = {}
    duplicates: list[str] = []
    for row_i, row in enumerate(rows, start=2):
        ts = (row.get("timestamp") or "").strip()
        if ts != selection_ts:
            continue
        cid = (row.get("contract_id") or "").strip()
        if not cid:
            continue
        if cid in per_contract:
            duplicates.append(cid)
        else:
            per_contract[cid] = (row, row_i)

    if duplicates:
        return None, [
            diag(
                code="SD750",
                severity=Severity.error,
                message=f"Duplicate candidate rows for contract_id at selection timestamp {selection_ts!r}: {sorted(set(duplicates))!r}",
                file=path,
                line=1,
                column=1,
            )
        ]

    candidates: list[OptionSelectionCandidate] = []
    diags: list[Diagnostic] = []

    for cid, row_pair in sorted(per_contract.items(), key=lambda kv: kv[0]):
        row, row_i = row_pair

        snap_d: dict = {"timestamp": selection_ts, "contract_id": cid}
        for k in _OPT_OPTIONAL_COLUMNS:
            if k in ("venue", "underlying", "expiry", "strike", "right", "lot"):
                continue
            if k in row:
                v = row.get(k)
                if v is not None and str(v).strip() != "":
                    if k in ("open_interest", "volume"):
                        snap_d[k] = str(v).strip()
                    elif k == "quality_flags":
                        flags = [x.strip() for x in str(v).split(",") if x.strip()]
                        snap_d[k] = flags
                    else:
                        snap_d[k] = str(v).strip()

        if "data_is_fresh" in row:
            raw = row.get("data_is_fresh")
            if raw is not None and str(raw).strip() != "":
                snap_d["data_is_fresh"] = _bool_optional(row, "data_is_fresh", default=True)

        snap, snap_diags = parse_option_snapshot_dict(snap_d, file=path, line=row_i, column=1)
        diags.extend(snap_diags)
        if snap is None:
            continue

        ok, _issues = check_option_snapshot_usable(snap)
        if not ok:
            continue

        underlying_price: Decimal | None = None
        raw_up = row.get("underlying_price")
        if raw_up is not None and str(raw_up).strip() != "":
            try:
                underlying_price = dec(str(raw_up).strip())
            except Exception:
                diags.append(
                    diag(
                        code="SD751",
                        severity=Severity.error,
                        message="Invalid underlying_price (expected decimal)",
                        file=path,
                        line=row_i,
                        column=1,
                    )
                )
                continue

        candidates.append(
            OptionSelectionCandidate(
                contract=snap.contract,
                canonical_id=snap.contract.canonical_id(),
                underlying_price=underlying_price,
                delta=snap.delta,
            )
        )

    if diags:
        return None, sorted(diags)

    if not candidates:
        return None, [
            diag(
                code="SD752",
                severity=Severity.error,
                message=f"No usable selection candidates at timestamp {selection_ts!r}",
                file=path,
                line=1,
                column=1,
            )
        ]

    selected, sel_diags = select_contract_id(req=req, candidates=candidates, file=path, line=1, column=1)
    if sel_diags:
        return None, sorted(sel_diags)
    assert selected is not None
    return selected, []


def load_option_events_csv(path: Path, *, contract_id: str | None = None) -> tuple[list[OptionEvent], list[Diagnostic]]:
    """
    Sprint v1.1-B: strict CSV loader for option snapshots (atomic contract-level events).

    CSV requirements (v1.1-B):
    - required columns: contract_id, timestamp
    - optional columns: bid/ask/last/close/iv/greeks/etc (see docs/options_contract_context.md)
    - if multiple distinct contract_id values exist:
      - require `contract_id` parameter (fail closed)
      - otherwise accept a single-contract series
    """

    events, _, diags = _load_option_events_csv_impl(path, contract_id=contract_id)
    return events, diags


def _load_option_events_csv_impl(
    path: Path, *, contract_id: str | None
) -> tuple[list[OptionEvent], CsvLoadMeta | None, list[Diagnostic]]:
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        return [], None, [diag(code="SD526", message="Option CSV is missing a header row", file=path)]

    missing = [c for c in _OPT_REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        return [], None, [
            diag(
                code="SD526",
                message=f"Option CSV is missing required column(s): {', '.join(missing)}",
                file=path,
                severity=Severity.error,
            )
        ]

    # First pass: collect distinct contract ids (deterministic selection).
    contract_ids: set[str] = set()
    rows = list(reader)
    for row in rows:
        cid = (row.get("contract_id") or "").strip()
        if cid:
            contract_ids.add(cid)

    if len(contract_ids) == 0:
        return [], CsvLoadMeta(columns=tuple(reader.fieldnames), row_count=0), [diag(code="SD523", message="CSV has no data rows", file=path)]

    selected = contract_id.strip() if contract_id is not None else None
    if len(contract_ids) > 1 and selected is None:
        return [], None, [
            diag(
                code="SD527",
                severity=Severity.error,
                message=(
                    "Option CSV contains multiple contract_id values; "
                    "provide --contract-id to select one deterministically"
                ),
                file=path,
            )
        ]

    if selected is not None:
        # Validate canonical id format early for deterministic errors.
        _, id_diags = parse_option_contract_id(selected, file=path, line=1, column=1)
        if id_diags:
            return [], None, sorted(id_diags)

    events: list[OptionEvent] = []
    diags: list[Diagnostic] = []

    for row_i, row in enumerate(rows, start=2):  # header is line 1
        cid = (row.get("contract_id") or "").strip()
        if not cid:
            diags.append(diag(code="SD721", message="Option CSV row has empty 'contract_id'", file=path, line=row_i, column=1))
            continue

        if selected is not None and cid != selected:
            continue

        ts = (row.get("timestamp") or "").strip()
        if not ts:
            diags.append(diag(code="SD720", message="Option CSV row has empty 'timestamp'", file=path, line=row_i, column=1))
            continue

        # Parse snapshot via v1.1-A parser for consistency/quantization.
        snap_d: dict = {"timestamp": ts, "contract_id": cid}
        for k in _OPT_OPTIONAL_COLUMNS:
            if k in ("venue", "underlying", "expiry", "strike", "right", "lot"):
                continue
            if k in row:
                v = row.get(k)
                if v is not None and str(v).strip() != "":
                    if k in ("open_interest", "volume"):
                        snap_d[k] = str(v).strip()
                    elif k == "quality_flags":
                        # comma-separated tokens
                        flags = [x.strip() for x in str(v).split(",") if x.strip()]
                        snap_d[k] = flags
                    else:
                        snap_d[k] = str(v).strip()

        if "data_is_fresh" in row:
            raw = row.get("data_is_fresh")
            if raw is not None and str(raw).strip() != "":
                snap_d["data_is_fresh"] = _bool_optional(row, "data_is_fresh", default=True)

        snap, snap_diags = parse_option_snapshot_dict(snap_d, file=path, line=row_i, column=1)
        diags.extend(snap_diags)
        if snap is None:
            continue

        # Cross-check identity columns if present (fail closed on mismatch).
        contract = snap.contract
        v = (row.get("venue") or "").strip()
        if v and v != contract.venue:
            diags.append(diag(code="SD728", message="venue column does not match contract_id", file=path, line=row_i, column=1))
            continue
        u = (row.get("underlying") or "").strip()
        if u and u != contract.underlying:
            diags.append(diag(code="SD728", message="underlying column does not match contract_id", file=path, line=row_i, column=1))
            continue
        ex = (row.get("expiry") or "").strip()
        if ex and ex != contract.expiry.isoformat():
            diags.append(diag(code="SD728", message="expiry column does not match contract_id", file=path, line=row_i, column=1))
            continue
        st = (row.get("strike") or "").strip()
        if st:
            try:
                st_d = dec(st)
            except Exception:
                diags.append(diag(code="SD704", message="Invalid strike column (expected decimal)", file=path, line=row_i, column=1))
                continue
            # strike column must match normalized strike exactly (2dp max).
            try:
                if abs(st_d.as_tuple().exponent) > 2:
                    diags.append(diag(code="SD704", message="Invalid strike column (expected <= 2 decimal places)", file=path, line=row_i, column=1))
                    continue
                if st_d.quantize(Decimal("0.01")) != contract.strike:
                    diags.append(diag(code="SD728", message="strike column does not match contract_id", file=path, line=row_i, column=1))
                    continue
            except Exception:
                diags.append(diag(code="SD704", message="Invalid strike column", file=path, line=row_i, column=1))
                continue
        r = (row.get("right") or "").strip()
        if r:
            rr = parse_option_right(r)
            if rr is None or rr.value != contract.right.value:
                diags.append(diag(code="SD728", message="right column does not match contract_id", file=path, line=row_i, column=1))
                continue
        lot = (row.get("lot") or "").strip()
        if lot:
            try:
                lot_i = int(lot)
            except Exception:
                diags.append(diag(code="SD706", message="Invalid lot column (expected int)", file=path, line=row_i, column=1))
                continue
            if lot_i != contract.lot_size:
                diags.append(diag(code="SD728", message="lot column does not match contract_id", file=path, line=row_i, column=1))
                continue

        try:
            session_is_regular = _bool_optional(row, "session_is_regular", default=True)
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        try:
            underlying_price = _dec_optional(row, "underlying_price")
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        try:
            uret = _dec_optional(row, "underlying_return_5m")
        except _FieldError as e:
            diags.append(diag(code="SD521", message=e.message, file=path, line=row_i, column=1))
            continue

        ok, issues = check_option_snapshot_usable(snap)
        if not ok:
            diags.append(
                diag(
                    code="SD734",
                    severity=Severity.error,
                    message=f"Option snapshot unusable: {', '.join(issues)}",
                    file=path,
                    line=row_i,
                    column=1,
                )
            )
            continue

        events.append(
            OptionEvent(
                symbol=contract.canonical_id(),
                index=len(events),
                timestamp=ts,
                snapshot=snap,
                underlying_price=underlying_price,
                session_is_regular=session_is_regular,
                underlying_return_5m=uret,
            )
        )

    if not events and not diags and selected is not None:
        diags.append(
            diag(
                code="SD736",
                severity=Severity.error,
                message=f"No rows found for selected contract_id: {selected!r}",
                file=path,
                line=1,
                column=1,
            )
        )
    elif not diags and not events:
        diags.append(diag(code="SD523", message="CSV has no data rows", file=path))

    meta = CsvLoadMeta(columns=tuple(reader.fieldnames), row_count=len(events))
    return events, meta, sorted(diags)


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
