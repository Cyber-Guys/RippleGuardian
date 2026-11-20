from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import (
    XRP,
    AccountLabel,
    AccountLabelKind,
    Amount,
    TraceParams,
    Transfer,
    TransferKind,
)
from ixh26.core.taint import trace

XRP1 = Decimal(1_000_000)
EXCHANGE = {"rEx": AccountLabel("rEx", AccountLabelKind.EXCHANGE, "Exchange")}


def tx(n: int, src: str, dst: str, xrp: int, tag: int | None = None) -> Transfer:
    return Transfer(
        tx_hash=f"{n:064X}",
        ledger_index=100 + n,
        tx_index=0,
        close_time=datetime(2026, 11, 20, tzinfo=UTC),
        kind=TransferKind.PAYMENT,
        source=src,
        destination=dst,
        amount=Amount(XRP, xrp * XRP1),
        destination_tag=tag,
    )


def params(stolen: int = 100, **kw: object) -> TraceParams:
    return TraceParams(origin="rV", asset=XRP, stolen_value=stolen * XRP1, start_ledger=100, **kw)


def test_split_and_exchange_sink_by_destination_tag() -> None:
    result = trace(
        params(),
        [
            tx(1, "rV", "rA", 100),
            tx(2, "rA", "rM1", 60),
            tx(3, "rA", "rM2", 40),
            tx(4, "rM1", "rEx", 60, tag=7),
            tx(5, "rM2", "rEx", 40, tag=7),
        ],
        labels=EXCHANGE,
    )
    (sink,) = result.sinks
    assert (sink.address, sink.destination_tag, sink.taint_value) == ("rEx", 7, 100 * XRP1)
    assert sink.hop == 3 and sink.label is not None
    assert [e.hop for e in result.edges] == [1, 2, 2, 3, 3]


def test_haircut_dilutes_with_clean_balance_and_ignores_earlier_outflows() -> None:
    result = trace(
        params(),
        [
            tx(1, "rA", "rEarly", 50),  # before any taint: clean
            tx(2, "rV", "rA", 100),
            tx(3, "rA", "rB", 75),  # rA holds 50 clean + 100 tainted -> 2/3 tainted
        ],
        opening_balances={"rA": 100 * XRP1},
    )
    by_dst = {e.transfer.destination: e for e in result.edges}
    assert "rEarly" not in by_dst
    assert by_dst["rB"].taint_value == 50 * XRP1
    assert by_dst["rB"].taint_ratio == Decimal(2) / 3


def test_merge_and_cycle_do_not_create_taint() -> None:
    result = trace(
        params(),
        [
            tx(1, "rV", "rA", 50),
            tx(2, "rV", "rB", 50),
            tx(3, "rA", "rC", 50),
            tx(4, "rB", "rC", 50),
            tx(5, "rC", "rA", 100),  # cycle back
            tx(6, "rA", "rC", 100),
        ],
    )
    total_sinks = sum(s.taint_value for s in result.sinks)
    assert total_sinks == 100 * XRP1


def test_stops_below_threshold_and_beyond_max_hops() -> None:
    small = trace(params(), [tx(1, "rV", "rA", 100), tx(2, "rA", "rDust", 0)])
    assert small.truncated is False  # zero-value transfers are ignored, not truncations
    cut = trace(
        params(),
        [tx(1, "rV", "rA", 100), tx(2, "rA", "rB", 100)],
        opening_balances={"rA": 20_000 * XRP1},  # 100 / 20100 * 100 XRP < 1% of 100 XRP
    )
    assert [e.transfer.destination for e in cut.edges] == ["rA"] and cut.truncated
    chain = [tx(i, f"r{i}", f"r{i + 1}", 100) for i in range(1, 10)]
    deep = trace(
        TraceParams(origin="r1", asset=XRP, stolen_value=100 * XRP1, start_ledger=0, max_hops=3),
        chain,
    )
    assert max(e.hop for e in deep.edges) == 3 and deep.truncated
