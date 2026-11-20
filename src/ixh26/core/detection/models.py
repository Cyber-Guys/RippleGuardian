"""Normalized inputs, thresholds, and evidence for the backend detectors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from ixh26.contracts import Amount, Asset, SecurityEvent, Transfer


@dataclass(frozen=True)
class LedgerPoint:
    tx_hash: str
    ledger_index: int
    tx_index: int
    close_time: datetime

    @property
    def order_key(self) -> tuple[int, int]:
        return self.ledger_index, self.tx_index


@dataclass(frozen=True)
class TradeFill:
    """An executed fill with identified sides, in units of base_amount.asset."""

    point: LedgerPoint
    buyer: str
    seller: str
    base_amount: Amount
    quote_asset: Asset
    fill_index: int = 0  # Distinguishes individual fills within the same transaction.
    first_positive_balance: bool = False  # Buyer crossed from zero to positive in this fill.
    from_amm: bool = False


@dataclass(frozen=True)
class PoolWithdrawal:
    """Reserves immediately before and after a successful XRP/issued-token AMM withdrawal."""

    point: LedgerPoint
    pool: str
    withdrawer: str
    token: Asset
    xrp_before_drops: int
    xrp_after_drops: int
    tokens_before: Decimal
    tokens_after: Decimal
    trading_fee: int = 0  # XRPL trading-fee units (100,000 equals 100%).

    def __post_init__(self) -> None:
        if self.token.is_xrp or not 0 <= self.trading_fee <= 1_000:
            raise ValueError("an XRP/token withdrawal needs an issued token and valid AMM fee")
        if not 0 <= self.xrp_after_drops <= self.xrp_before_drops:
            raise ValueError("XRP reserve must be nonnegative and cannot grow in a withdrawal")
        if not 0 <= self.tokens_after <= self.tokens_before:
            raise ValueError("token reserve must be nonnegative and cannot grow in a withdrawal")


@dataclass(frozen=True)
class SigningChange:
    event: SecurityEvent
    tx_index: int  # Required to order the change and subsequent transfers in the same ledger.

    @property
    def order_key(self) -> tuple[int, int]:
        return self.event.ledger_index, self.tx_index


@dataclass(frozen=True)
class BalanceBefore:
    tx_hash: str
    account: str
    amount: Amount


@dataclass(frozen=True)
class DetectionBatch:
    """One bounded batch of validated activity, including history for lookback windows."""

    transfers: tuple[Transfer, ...] = ()
    fills: tuple[TradeFill, ...] = ()
    withdrawals: tuple[PoolWithdrawal, ...] = ()
    signing_changes: tuple[SigningChange, ...] = ()
    balances_before: tuple[BalanceBefore, ...] = ()
    known_destinations: frozenset[tuple[str, str, int | None]] = frozenset()
    excluded_funnel_destinations: frozenset[str] = frozenset()


@dataclass(frozen=True)
class DetectionSettings:
    """Tunable starting values for replay and testing, pending historical calibration."""

    funnel_window: timedelta = timedelta(minutes=30)
    funnel_min_senders: int = 3
    funnel_min_fraction: Decimal = Decimal("0.8")
    wash_window: timedelta = timedelta(minutes=30)
    wash_min_fills: int = 6
    wash_max_wallets: int = 6
    wash_max_net_ratio: Decimal = Decimal("0.15")
    wash_min_market_share: Decimal = Decimal("0.5")
    liquidity_window: timedelta = timedelta(hours=1)
    liquidity_min_buyers: int = 3
    liquidity_min_pool_drops: int = 10_000_000
    liquidity_min_drop: Decimal = Decimal("0.5")
    liquidity_sale_size: Decimal = Decimal(1_000)
    takeover_window: timedelta = timedelta(minutes=15)
    takeover_min_outflow: Decimal = Decimal("0.7")

    def __post_init__(self) -> None:
        windows = (
            self.funnel_window,
            self.wash_window,
            self.liquidity_window,
            self.takeover_window,
        )
        if min(windows) <= timedelta(0):
            raise ValueError("detection windows must be positive")
        fractions = (
            self.funnel_min_fraction,
            self.wash_min_market_share,
            self.liquidity_min_drop,
            self.takeover_min_outflow,
        )
        if any(not 0 < value <= 1 for value in fractions) or not 0 <= self.wash_max_net_ratio <= 1:
            raise ValueError("detection ratios must be within their unit interval")
        if min(self.funnel_min_senders, self.wash_min_fills, self.wash_max_wallets) < 2:
            raise ValueError(
                "funnel and wash thresholds require at least two participants or fills"
            )
        if (
            min(self.liquidity_min_buyers, self.liquidity_min_pool_drops, self.liquidity_sale_size)
            <= 0
        ):
            raise ValueError("liquidity detection thresholds must be positive")


class FindingKind(StrEnum):
    FUNDS_FUNNEL = "funds_funnel"
    POSSIBLE_WASH_TRADING = "possible_wash_trading"
    POOL_LIQUIDITY_DROP = "pool_liquidity_drop"
    POSSIBLE_TAKEOVER = "possible_takeover"


@dataclass(frozen=True)
class Finding:
    """A review signal anchored to a transaction and supported by its listed evidence."""

    kind: FindingKind
    subject: str
    asset: Asset
    trigger: LedgerPoint
    evidence_hashes: tuple[str, ...]
    metrics: tuple[tuple[str, int | Decimal | str], ...]


def transfer_point(transfer: Transfer) -> LedgerPoint:
    return LedgerPoint(
        transfer.tx_hash, transfer.ledger_index, transfer.tx_index, transfer.close_time
    )
