from decimal import Decimal

from sigmadsl.chain_metrics import (
    UNKNOWN,
    iv_skew,
    oi_change,
    oi_change_calls,
    oi_change_puts,
    pcr_oi,
    pcr_volume,
)
from sigmadsl.chain_snapshots import ChainSnapshot
from sigmadsl.options_snapshots import OptionSnapshot
from sigmadsl.options_contracts import parse_option_contract_id


def _snap(
    *,
    ts: str,
    call_oi: int,
    put_oi: int,
    call_vol: int,
    put_vol: int,
    call_iv: str,
    put_iv: str,
) -> ChainSnapshot:
    call_c, _ = parse_option_contract_id("OPT:NSE:INFY:2026-01-29:1500:CALL:300")
    put_c, _ = parse_option_contract_id("OPT:NSE:INFY:2026-01-29:1500:PUT:300")
    assert call_c is not None and put_c is not None

    call = OptionSnapshot(timestamp=ts, contract=call_c, last=Decimal("1"), open_interest=call_oi, volume=call_vol, iv=Decimal(call_iv))
    put = OptionSnapshot(timestamp=ts, contract=put_c, last=Decimal("1"), open_interest=put_oi, volume=put_vol, iv=Decimal(put_iv))
    return ChainSnapshot(
        timestamp=ts,
        venue="NSE",
        underlying="INFY",
        expiries=("2026-01-29",),
        contracts=(call, put),
        data_is_fresh=True,
        quality_flags=(),
        is_complete=True,
        has_unknowns=False,
    )


def test_chain_metrics_pcr_oi_and_volume_and_skew_quantized():
    s = _snap(ts="2026-01-01T09:15:00", call_oi=1000, put_oi=1500, call_vol=200, put_vol=250, call_iv="0.200000", put_iv="0.240000")
    assert pcr_oi(s) == Decimal("1.5000")
    assert pcr_volume(s) == Decimal("1.2500")
    assert iv_skew(s) == Decimal("0.040000")


def test_chain_metrics_oi_change_requires_prior_snapshot():
    s0 = _snap(ts="2026-01-01T09:15:00", call_oi=1000, put_oi=1500, call_vol=200, put_vol=250, call_iv="0.200000", put_iv="0.240000")
    s1 = _snap(ts="2026-01-01T09:20:00", call_oi=900, put_oi=1700, call_vol=210, put_vol=260, call_iv="0.190000", put_iv="0.250000")
    assert oi_change(None, s0) is UNKNOWN
    assert oi_change_puts(None, s0) is UNKNOWN
    assert oi_change_calls(None, s0) is UNKNOWN

    assert oi_change(s0, s1) == Decimal("100")
    assert oi_change_puts(s0, s1) == Decimal("200")
    assert oi_change_calls(s0, s1) == Decimal("-100")


def test_chain_metrics_fail_closed_on_zero_denominator():
    s = _snap(ts="2026-01-01T09:15:00", call_oi=0, put_oi=100, call_vol=10, put_vol=10, call_iv="0.200000", put_iv="0.240000")
    assert pcr_oi(s) is UNKNOWN

