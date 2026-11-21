"""Rules for repeated trade turnover and withdrawals from XRP/token pools."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from ixh26.contracts import XRP, Asset
from ixh26.core.detection.models import (
    DetectionSettings,
    Finding,
    FindingKind,
    PoolWithdrawal,
    TradeFill,
)


def _repeated_trade_group(window: deque[TradeFill], buyer: str, min_pair_fills: int) -> set[str]:
    pair_counts = Counter(frozenset((fill.buyer, fill.seller)) for fill in window)
    neighbors: defaultdict[str, set[str]] = defaultdict(set)
    for pair, count in pair_counts.items():
        if count >= min_pair_fills:
            first, second = pair
            neighbors[first].add(second)
            neighbors[second].add(first)

    group = {buyer}
    remaining = [buyer]
    while remaining:
        new_wallets = neighbors[remaining.pop()] - group
        group.update(new_wallets)
        remaining.extend(new_wallets)
    return group


def detect_wash_trading(fills: Sequence[TradeFill], settings: DetectionSettings) -> list[Finding]:
    """Flag concentrated order-book turnover that leaves little change in wallet holdings."""
    windows: defaultdict[tuple[Asset, Asset], deque[TradeFill]] = defaultdict(deque)
    last_alert: dict[tuple[Asset, Asset, tuple[str, ...]], datetime] = {}
    findings: list[Finding] = []
    for fill in fills:
        if fill.from_amm:
            continue
        market = fill.base_amount.asset, fill.quote_asset
        window = windows[market]
        now = fill.point.close_time
        while window and now - window[0].point.close_time > settings.wash_window:
            window.popleft()
        window.append(fill)
        if len(window) < settings.wash_min_fills:
            continue

        group = _repeated_trade_group(window, fill.buyer, settings.wash_min_pair_fills)
        if fill.seller not in group or len(group) > settings.wash_max_wallets:
            continue
        internal = [trade for trade in window if {trade.buyer, trade.seller} <= group]
        if len(internal) < settings.wash_min_fills:
            continue
        volume = sum(trade.base_amount.value for trade in internal)
        market_volume = sum(trade.base_amount.value for trade in window)
        share = volume / market_volume
        if share < settings.wash_min_market_share:
            continue

        net_by_wallet: defaultdict[str, Decimal] = defaultdict(Decimal)
        for trade in internal:
            net_by_wallet[trade.buyer] += trade.base_amount.value
            net_by_wallet[trade.seller] -= trade.base_amount.value
        net_ratio = sum(abs(net) for net in net_by_wallet.values()) / (2 * volume)
        if net_ratio > settings.wash_max_net_ratio:
            continue

        wallets = tuple(sorted(group))
        signature = (*market, wallets)
        if signature in last_alert and now - last_alert[signature] <= settings.wash_window:
            continue
        last_alert[signature] = now
        findings.append(
            Finding(
                FindingKind.POSSIBLE_WASH_TRADING,
                f"{market[0]}/{market[1]}",
                market[0],
                fill.point,
                tuple(dict.fromkeys(trade.point.tx_hash for trade in internal)),
                (
                    ("wallets", ", ".join(wallets)),
                    ("fill_count", len(internal)),
                    ("base_volume", volume),
                    ("observed_order_book_volume_share", share),
                    ("net_to_gross_ratio", net_ratio),
                ),
            )
        )
    return findings


def _sale_quote_drops(xrp: int, tokens: Decimal, sale_size: Decimal, fee: int) -> int:
    """Estimate AMM proceeds, before issuer transfer fees or alternate routing."""
    if xrp == 0 or tokens == 0:
        return 0
    effective_input = sale_size * (1 - Decimal(fee) / 100_000)
    return int(xrp * effective_input / (tokens + effective_input))


def detect_liquidity_drops(
    withdrawals: Sequence[PoolWithdrawal], fills: Sequence[TradeFill], settings: DetectionSettings
) -> list[Finding]:
    """Find material withdrawals after purchases that give wallets a positive balance."""
    new_buyers: defaultdict[Asset, deque[TradeFill]] = defaultdict(deque)
    first_buys = iter(
        fill for fill in fills if fill.quote_asset == XRP and fill.first_positive_balance
    )
    next_buy = next(first_buys, None)
    findings: list[Finding] = []
    for withdrawal in withdrawals:
        while next_buy is not None and next_buy.point.order_key < withdrawal.point.order_key:
            new_buyers[next_buy.base_amount.asset].append(next_buy)
            next_buy = next(first_buys, None)

        if withdrawal.xrp_before_drops < settings.liquidity_min_pool_drops:
            continue
        removed = withdrawal.xrp_before_drops - withdrawal.xrp_after_drops
        drop = Decimal(removed) / withdrawal.xrp_before_drops
        if drop < settings.liquidity_min_drop:
            continue

        window = new_buyers[withdrawal.token]
        now = withdrawal.point.close_time
        while window and now - window[0].point.close_time > settings.liquidity_window:
            window.popleft()
        buys = [fill for fill in window if fill.buyer != withdrawal.withdrawer]
        buyer_count = len({fill.buyer for fill in buys})
        if buyer_count < settings.liquidity_min_buyers:
            continue

        sale_size = settings.liquidity_sale_size
        before = _sale_quote_drops(
            withdrawal.xrp_before_drops, withdrawal.tokens_before, sale_size, withdrawal.trading_fee
        )
        after = _sale_quote_drops(
            withdrawal.xrp_after_drops, withdrawal.tokens_after, sale_size, withdrawal.trading_fee
        )
        findings.append(
            Finding(
                FindingKind.POOL_LIQUIDITY_DROP,
                withdrawal.pool,
                withdrawal.token,
                withdrawal.point,
                tuple(
                    dict.fromkeys(
                        [*(fill.point.tx_hash for fill in buys), withdrawal.point.tx_hash]
                    )
                ),
                (
                    ("withdrawing_wallet", withdrawal.withdrawer),
                    ("new_buyers", buyer_count),
                    ("xrp_before_drops", withdrawal.xrp_before_drops),
                    ("xrp_after_drops", withdrawal.xrp_after_drops),
                    ("xrp_reserve_drop_fraction", drop),
                    ("sale_size_tokens", sale_size),
                    ("amm_quote_before_drops", before),
                    ("amm_quote_after_drops", after),
                ),
            )
        )
    return findings
