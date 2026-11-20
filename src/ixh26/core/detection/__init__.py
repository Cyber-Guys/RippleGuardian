"""Backend entry point for explainable rules over normalized XRPL activity."""

from __future__ import annotations

from ixh26.core.detection.markets import detect_liquidity_drops, detect_wash_trading
from ixh26.core.detection.models import (
    BalanceBefore,
    DetectionBatch,
    DetectionSettings,
    Finding,
    FindingKind,
    LedgerPoint,
    PoolWithdrawal,
    SigningChange,
    TradeFill,
)
from ixh26.core.detection.wallets import detect_funnels, detect_takeovers

__all__ = [
    "BalanceBefore",
    "DetectionBatch",
    "DetectionSettings",
    "Finding",
    "FindingKind",
    "LedgerPoint",
    "PoolWithdrawal",
    "SigningChange",
    "TradeFill",
    "detect",
]


def detect(batch: DetectionBatch, settings: DetectionSettings | None = None) -> tuple[Finding, ...]:
    """Run all four rules in canonical ledger order, retaining transaction evidence."""
    settings = settings if settings is not None else DetectionSettings()
    transfers = sorted(dict.fromkeys(batch.transfers), key=lambda item: item.order_key)
    fills = sorted(
        (
            fill
            for fill in dict.fromkeys(batch.fills)
            if fill.base_amount.value > 0 and fill.buyer != fill.seller
        ),
        key=lambda item: (item.point.order_key, item.fill_index),
    )
    withdrawals = sorted(dict.fromkeys(batch.withdrawals), key=lambda item: item.point.order_key)
    findings = (
        detect_funnels(batch, settings, transfers)
        + detect_wash_trading(fills, settings)
        + detect_liquidity_drops(withdrawals, fills, settings)
        + detect_takeovers(batch, settings, transfers)
    )
    return tuple(
        sorted(findings, key=lambda item: (item.trigger.order_key, item.kind, item.subject))
    )
