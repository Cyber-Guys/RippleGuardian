from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ixh26.contracts import (
    XRP,
    Amount,
    Asset,
    SecurityEvent,
    SecurityEventKind,
    Transfer,
    TransferKind,
)
from ixh26.core.detection import (
    BalanceBefore,
    DetectionBatch,
    FindingKind,
    LedgerPoint,
    PoolWithdrawal,
    SigningChange,
    TradeFill,
    detect,
)

# SIMULATED: offline events use synthetic identifiers and balances only.
TOKEN = Asset("USD", "issuer-A")
OTHER_TOKEN = Asset("USD", "issuer-B")
START = datetime(2026, 11, 20, tzinfo=UTC)


def _point(index: int) -> LedgerPoint:
    return LedgerPoint(f"simulated:{index}", 1, index, START + timedelta(seconds=index))


def _transfer(
    index: int,
    sender: str,
    destination: str,
    value: int,
    *,
    asset: Asset = TOKEN,
    tag: int | None = None,
) -> Transfer:
    point = _point(index)
    return Transfer(
        tx_hash=point.tx_hash,
        ledger_index=point.ledger_index,
        tx_index=point.tx_index,
        close_time=point.close_time,
        kind=TransferKind.PAYMENT,
        source=sender,
        destination=destination,
        amount=Amount(asset, Decimal(value)),
        destination_tag=tag,
    )


def _funnel() -> tuple[Transfer, ...]:
    incoming = tuple(_transfer(i, "origin", f"wallet-{i}", 100) for i in range(3))
    outgoing = tuple(_transfer(i + 3, f"wallet-{i}", "hub", 90, tag=0) for i in range(3))
    return incoming + outgoing


def test_funnel_orders_activity_preserves_tag_zero_and_deduplicates():
    transfers = _funnel()
    (finding,) = detect(DetectionBatch(transfers=tuple(reversed(transfers)) + transfers[-1:]))
    assert finding.kind == FindingKind.FUNDS_FUNNEL
    assert finding.subject == "hub:0"
    assert dict(finding.metrics) == {"sender_count": 3, "matched_inflow_upper_bound": Decimal(270)}
    assert set(finding.evidence_hashes) == {transfer.tx_hash for transfer in transfers}


def test_funnel_keeps_different_customers_and_issuers_separate():
    transfers = _funnel()
    different_tag = replace(transfers[-1], destination_tag=1)
    assert detect(DetectionBatch(transfers=(*transfers[:-1], different_tag))) == ()
    other_credit = replace(transfers[2], amount=Amount(OTHER_TOKEN, Decimal(100)))
    assert detect(DetectionBatch(transfers=(*transfers[:2], other_credit, *transfers[3:]))) == ()


def test_funnel_does_not_reuse_already_debited_credits():
    transfers = _funnel()
    debit = _transfer(3, "wallet-2", "unrelated", 70)
    assert detect(DetectionBatch(transfers=(*transfers[:3], debit, *transfers[3:]))) == ()
    assert detect(DetectionBatch(transfers=transfers, excluded_funnel_destinations={"hub"})) == ()


def _fill(
    index: int, buyer: str, seller: str, *, token: Asset = TOKEN, first: bool = False
) -> TradeFill:
    return TradeFill(
        _point(index), buyer, seller, Amount(token, Decimal(10)), XRP, first_positive_balance=first
    )


def test_wash_trading_uses_wallet_net_positions_and_counts_each_fill_once():
    fills = tuple(_fill(i, *pair) for i, pair in enumerate([("a", "b"), ("b", "a")] * 3))
    (finding,) = detect(DetectionBatch(fills=tuple(reversed(fills)) + fills[-1:]))
    assert finding.kind is FindingKind.POSSIBLE_WASH_TRADING
    assert dict(finding.metrics)["fill_count"] == 6
    assert dict(finding.metrics)["base_volume"] == Decimal(60)
    assert dict(finding.metrics)["net_to_gross_ratio"] == Decimal(0)
    assert len(finding.evidence_hashes) == 6


def test_wash_trading_requires_individual_balances_to_return_near_start():
    fills = tuple(_fill(i, "a", "b") for i in range(6))
    assert detect(DetectionBatch(fills=fills)) == ()
    amm = tuple(replace(fill, from_amm=True) for fill in fills)
    assert detect(DetectionBatch(fills=amm)) == ()


def _withdrawal() -> PoolWithdrawal:
    return PoolWithdrawal(
        _point(9),
        "pool",
        "provider",
        TOKEN,
        1_000_000_000,
        100_000_000,
        Decimal(10_000),
        Decimal(1_000),
    )


def test_liquidity_drop_explains_fixed_sale_impact_in_drops():
    fills = tuple(_fill(i, f"buyer-{i}", "pool", first=True) for i in range(3))
    withdrawal = _withdrawal()
    (finding,) = detect(DetectionBatch(fills=fills, withdrawals=(withdrawal, withdrawal)))
    assert finding.kind == FindingKind.POOL_LIQUIDITY_DROP
    assert finding.trigger == withdrawal.point
    metrics = dict(finding.metrics)
    assert metrics["new_buyers"] == 3
    assert metrics["xrp_reserve_drop_fraction"] == Decimal("0.9")
    assert metrics["amm_quote_before_drops"] == 90_909_090
    assert metrics["amm_quote_after_drops"] == 50_000_000


def test_liquidity_drop_ignores_future_buys_other_issuers_and_small_withdrawals():
    two_buys = (_fill(0, "a", "pool", first=True), _fill(1, "b", "pool", first=True))
    withdrawal = _withdrawal()
    fillers = (*two_buys, _fill(2, "c", "pool", token=OTHER_TOKEN, first=True))
    assert detect(DetectionBatch(fills=fillers, withdrawals=(withdrawal,))) == ()
    future = (*two_buys, _fill(10, "c", "pool", first=True))
    assert detect(DetectionBatch(fills=future, withdrawals=(withdrawal,))) == ()
    small = replace(withdrawal, xrp_after_drops=900_000_000)
    timely = (*two_buys, _fill(2, "c", "pool", first=True))
    assert detect(DetectionBatch(fills=timely, withdrawals=(small,))) == ()


def _signing_change() -> SigningChange:
    point = _point(2)
    return SigningChange(
        SecurityEvent(
            point.tx_hash, 1, point.close_time, "watched", SecurityEventKind.SET_REGULAR_KEY
        ),
        tx_index=point.tx_index,
    )


def test_takeover_accumulates_new_outflows_after_key_change_within_one_ledger():
    first = _transfer(3, "watched", "new-1", 40)
    second = _transfer(4, "watched", "new-2", 40)
    change = _signing_change()
    balance = BalanceBefore(first.tx_hash, "watched", Amount(TOKEN, Decimal(100)))
    (finding,) = detect(
        DetectionBatch(
            transfers=(second, first), signing_changes=(change,), balances_before=(balance,)
        )
    )
    assert finding.kind == FindingKind.POSSIBLE_TAKEOVER
    assert finding.evidence_hashes == (change.event.tx_hash, first.tx_hash, second.tx_hash)
    assert dict(finding.metrics)["outflow_fraction_of_starting_balance"] == Decimal("0.8")


@pytest.mark.parametrize("index,already_known", [(1, False), (3, True), (3600, False)])
def test_takeover_requires_order_window_and_a_novel_destination(index, already_known):
    outgoing = _transfer(index, "watched", "other", 90)
    balance = BalanceBefore(outgoing.tx_hash, "watched", Amount(TOKEN, Decimal(100)))
    known = frozenset({("watched", "other", None)}) if already_known else frozenset()
    assert (
        detect(
            DetectionBatch(
                transfers=(outgoing,),
                signing_changes=(_signing_change(),),
                balances_before=(balance,),
                known_destinations=known,
            )
        )
        == ()
    )
