"""Alert rules: what a wallet owner should hear about one ledger event. Pure functions.

Each rule turns one event into zero or more ``Alert``s addressed to a wallet. Who watches that
wallet, and whether they muted the alert, is decided later by ``flows/monitor.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ixh26.contracts import (
    Alert,
    AlertKind,
    AlertSeverity,
    Amount,
    SecurityEvent,
    Transfer,
)

DROPS_PER_XRP = Decimal(1_000_000)


@dataclass(frozen=True)
class FlagNote:
    """What users are told about a flagged account or transaction."""

    category: str
    reason: str


def amount_text(amount: Amount) -> str:
    """``Amount(XRP, 1500000)`` -> ``"1.5 XRP"``; tokens keep their own units."""
    if amount.asset.is_xrp:
        return f"{(amount.value / DROPS_PER_XRP).normalize():f} XRP"
    return f"{amount.value.normalize():f} {amount.asset.currency}"


def short(address: str) -> str:
    """``rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY`` -> ``rPEPPE…6GDY``."""
    return f"{address[:6]}…{address[-4:]}"


def security_alert(event: SecurityEvent, now: datetime) -> Alert:
    """A signing-key change is the first sign of a takeover: always critical."""
    detail = f" ({event.detail})" if event.detail else ""
    return Alert(
        wallet=event.account,
        kind=AlertKind.SECURITY_CHANGE,
        severity=AlertSeverity.CRITICAL,
        tx_hash=event.tx_hash,
        message=(
            f"Signing configuration changed: {event.kind.value.replace('_', ' ')}{detail}. "
            "If this wasn't you, your keys may be compromised."
        ),
        created_at=now,
    )


def outgoing_alert(transfer: Transfer, now: datetime) -> Alert:
    """Money left the wallet. The per-wallet threshold is applied by the caller."""
    tag = f" (tag {transfer.destination_tag})" if transfer.destination_tag is not None else ""
    return Alert(
        wallet=transfer.source,
        kind=AlertKind.OUTGOING_PAYMENT,
        severity=AlertSeverity.WARNING,
        tx_hash=transfer.tx_hash,
        message=f"Sent {amount_text(transfer.amount)} to {short(transfer.destination)}{tag}.",
        created_at=now,
    )


def flagged_contact_alerts(
    transfer: Transfer, flags: Mapping[str, FlagNote], now: datetime
) -> list[Alert]:
    """Warn both sides when either the counterparty or the tx itself was flagged."""
    alerts = []
    sides = (
        (transfer.source, transfer.destination, "Sent funds to"),
        (transfer.destination, transfer.source, "Received funds from"),
    )
    for wallet, other, verb in sides:
        flag = flags.get(other) or flags.get(transfer.tx_hash.upper())
        if flag is None:
            continue
        alerts.append(
            Alert(
                wallet=wallet,
                kind=AlertKind.FLAGGED_COUNTERPARTY,
                severity=AlertSeverity.CRITICAL,
                tx_hash=transfer.tx_hash,
                message=(
                    f"{verb} {short(other)}, flagged by an analyst as {flag.category}: "
                    f"{flag.reason}"
                ),
                created_at=now,
            )
        )
    return alerts


def alerts_for(
    transfers: list[Transfer],
    events: list[SecurityEvent],
    flags: Mapping[str, FlagNote],
    now: datetime,
) -> list[Alert]:
    """Every alert the new ledger activity deserves, before owners' preferences."""
    alerts = [security_alert(e, now) for e in events]
    for t in transfers:
        alerts.append(outgoing_alert(t, now))
        alerts.extend(flagged_contact_alerts(t, flags, now))
    return alerts


def exchange_alert(
    victim: str, place: str, tag: int | None, value_text: str, tx_hash: str, now: datetime
) -> Alert:
    """Tell the victim which known entity received their stolen funds, and under which tag."""
    tag_text = f" with destination tag {tag}" if tag is not None else ""
    return Alert(
        wallet=victim,
        kind=AlertKind.TAINT_AT_EXCHANGE,
        severity=AlertSeverity.CRITICAL,
        tx_hash=tx_hash,
        message=(
            f"Traced {value_text} of your stolen funds to {place}{tag_text}. "
            "Share this with the exchange and the police."
        ),
        created_at=now,
    )
