from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .diagnostics import Diagnostic, Severity, diag
from .options_contracts import OptionContract, parse_option_contract_id
from .runtime_models import dec, dec_str


GREEK_QUANTUM = Decimal("0.00000001")  # 8 dp
IV_QUANTUM = Decimal("0.000001")  # 6 dp (ratio, e.g. 0.25 = 25%)


def _quantize_optional(v: Decimal | None, q: Decimal) -> Decimal | None:
    if v is None:
        return None
    return v.quantize(q)


@dataclass(frozen=True)
class OptionSnapshot:
    """
    v1.1-A: atomic option contract snapshot inputs.

    Notes:
    - values are Decimal for determinism (no float)
    - `data_is_fresh` is an explicit guard flag; the engine does not infer staleness yet
    - IV is represented as a ratio in [0,1] when provided (consistent with Percent-as-ratio in the DSL)
    """

    timestamp: str
    contract: OptionContract
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    close: Decimal | None = None
    iv: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    open_interest: int | None = None
    volume: int | None = None
    data_is_fresh: bool = True
    quality_flags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "contract_id": self.contract.canonical_id(),
            "bid": dec_str(self.bid) if self.bid is not None else None,
            "ask": dec_str(self.ask) if self.ask is not None else None,
            "last": dec_str(self.last) if self.last is not None else None,
            "close": dec_str(self.close) if self.close is not None else None,
            "iv": dec_str(self.iv) if self.iv is not None else None,
            "delta": dec_str(self.delta) if self.delta is not None else None,
            "gamma": dec_str(self.gamma) if self.gamma is not None else None,
            "theta": dec_str(self.theta) if self.theta is not None else None,
            "vega": dec_str(self.vega) if self.vega is not None else None,
            "open_interest": self.open_interest,
            "volume": self.volume,
            "data_is_fresh": self.data_is_fresh,
            "quality_flags": list(self.quality_flags),
        }


def parse_option_snapshot_dict(
    d: dict,
    *,
    file: Path | None = None,
    line: int | None = None,
    column: int | None = None,
) -> tuple[OptionSnapshot | None, list[Diagnostic]]:
    """
    Parse an option snapshot dictionary for fixtures/tests (v1.1-A).
    """

    diags: list[Diagnostic] = []
    ts = d.get("timestamp")
    if not isinstance(ts, str) or not ts:
        diags.append(
            diag(
                code="SD720",
                severity=Severity.error,
                message="Option snapshot missing/invalid timestamp",
                file=file,
                line=line,
                column=column,
            )
        )

    cid = d.get("contract_id")
    if not isinstance(cid, str) or not cid:
        diags.append(
            diag(
                code="SD721",
                severity=Severity.error,
                message="Option snapshot missing/invalid contract_id",
                file=file,
                line=line,
                column=column,
            )
        )
        return None, sorted(diags)

    contract, cd = parse_option_contract_id(cid, file=file, line=line, column=column)
    diags.extend(cd)
    if diags:
        return None, sorted(diags)
    assert contract is not None

    def _dec_opt(key: str, *, code: str, quantum: Decimal | None = None) -> Decimal | None:
        v = d.get(key)
        if v is None:
            return None
        try:
            dv = dec(v)
        except Exception:
            diags.append(
                diag(code=code, severity=Severity.error, message=f"Invalid decimal for {key!r}", file=file, line=line, column=column)
            )
            return None
        return dv.quantize(quantum) if quantum is not None else dv

    bid = _dec_opt("bid", code="SD722")
    ask = _dec_opt("ask", code="SD723")
    last = _dec_opt("last", code="SD724")
    close = _dec_opt("close", code="SD724")
    iv = _dec_opt("iv", code="SD725", quantum=IV_QUANTUM)
    delta = _dec_opt("delta", code="SD726", quantum=GREEK_QUANTUM)
    gamma = _dec_opt("gamma", code="SD727", quantum=GREEK_QUANTUM)
    theta = _dec_opt("theta", code="SD728", quantum=GREEK_QUANTUM)
    vega = _dec_opt("vega", code="SD729", quantum=GREEK_QUANTUM)

    oi = d.get("open_interest")
    if oi is not None:
        try:
            oi = int(oi)
        except Exception:
            diags.append(
                diag(code="SD730", severity=Severity.error, message="Invalid open_interest (expected int)", file=file, line=line, column=column)
            )
            oi = None
        else:
            if oi < 0:
                diags.append(
                    diag(code="SD730", severity=Severity.error, message="Invalid open_interest (expected >= 0)", file=file, line=line, column=column)
                )
                oi = None

    vol = d.get("volume")
    if vol is not None:
        try:
            vol = int(vol)
        except Exception:
            diags.append(
                diag(code="SD731", severity=Severity.error, message="Invalid volume (expected int)", file=file, line=line, column=column)
            )
            vol = None
        else:
            if vol < 0:
                diags.append(
                    diag(code="SD731", severity=Severity.error, message="Invalid volume (expected >= 0)", file=file, line=line, column=column)
                )
                vol = None

    data_is_fresh = d.get("data_is_fresh", True)
    if not isinstance(data_is_fresh, bool):
        diags.append(
            diag(code="SD732", severity=Severity.error, message="Invalid data_is_fresh (expected bool)", file=file, line=line, column=column)
        )
        data_is_fresh = True

    flags = d.get("quality_flags", [])
    if flags is None:
        flags = []
    if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
        diags.append(
            diag(code="SD733", severity=Severity.error, message="Invalid quality_flags (expected list[str])", file=file, line=line, column=column)
        )
        flags = []

    if diags:
        return None, sorted(diags)

    assert isinstance(ts, str)
    return (
        OptionSnapshot(
            timestamp=ts,
            contract=contract,
            bid=bid,
            ask=ask,
            last=last,
            close=close,
            iv=iv,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            open_interest=oi,
            volume=vol,
            data_is_fresh=data_is_fresh,
            quality_flags=tuple(sorted(flags)),
        ),
        [],
    )


def check_option_snapshot_usable(
    snap: OptionSnapshot,
    *,
    require_quote: bool = True,
) -> tuple[bool, tuple[str, ...]]:
    """
    v1.1-A: conservative quality guard helper.

    Rules:
    - if `data_is_fresh` is False => unusable
    - if `require_quote` => require at least one quote field (last or both bid+ask)
    """

    issues: list[str] = []
    if not snap.data_is_fresh:
        issues.append("data_is_fresh=false")
    if snap.quality_flags:
        issues.append("quality_flags_present")

    if require_quote:
        has_last = snap.last is not None
        has_close = snap.close is not None
        has_bid_ask = snap.bid is not None and snap.ask is not None
        if not (has_last or has_close or has_bid_ask):
            issues.append("missing_quote")

    return (len(issues) == 0), tuple(sorted(issues))
