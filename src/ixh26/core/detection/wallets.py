"""Temporal rules for grouped transfers and watched-wallet signing changes."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import groupby

from ixh26.contracts import Asset, SecurityEventKind, Transfer, TransferKind
from ixh26.core.detection.models import (
    DetectionBatch,
    DetectionSettings,
    Finding,
    FindingKind,
    SigningChange,
    transfer_point,
)


@dataclass
class _Credit:
    time: datetime
    tx_hash: str
    remaining: Decimal


@dataclass(frozen=True)
class _Forward:
    transfer: Transfer
    amount: Decimal
    incoming_hashes: tuple[str, ...]


def _match_recent_credits(
    credits: deque[_Credit], transfer: Transfer, window: timedelta
) -> tuple[Decimal, Decimal, tuple[str, ...]]:
    while credits and transfer.close_time - credits[0].time > window:
        credits.popleft()
    available = sum((credit.remaining for credit in credits), Decimal(0))
    debited = (transfer.source_amount or transfer.amount).value
    matched = min(available, debited)
    unmatched = matched
    hashes: list[str] = []
    while credits and unmatched > 0:
        credit = credits[0]
        used = min(credit.remaining, unmatched)
        credit.remaining -= used
        unmatched -= used
        hashes.append(credit.tx_hash)
        if credit.remaining == 0:
            credits.popleft()
    return matched, available, tuple(hashes)


def detect_funnels(
    batch: DetectionBatch, settings: DetectionSettings, transfers: Sequence[Transfer]
) -> list[Finding]:
    """Look for distinct accounts passing recent deposits to the same destination."""
    credits: defaultdict[tuple[str, Asset], deque[_Credit]] = defaultdict(deque)
    routes: defaultdict[tuple[str, int | None, Asset], deque[_Forward]] = defaultdict(deque)
    last_alert: dict[tuple[str, int | None, Asset], datetime] = {}
    findings: list[Finding] = []

    for _, legs in groupby(transfers, key=lambda transfer: transfer.order_key):
        transaction = tuple(legs)
        for transfer in transaction:
            debited = transfer.source_amount or transfer.amount
            key = (transfer.source, debited.asset)
            if debited.value <= 0 or key not in credits:
                continue
            matched, available, hashes = _match_recent_credits(
                credits[key], transfer, settings.funnel_window
            )
            if not credits[key]:
                del credits[key]
            forwarded = min(matched, transfer.amount.value)
            if (
                transfer.kind != TransferKind.PAYMENT
                or transfer.source == transfer.destination
                or transfer.destination in batch.excluded_funnel_destinations
                or debited.asset != transfer.amount.asset
                or forwarded < settings.funnel_min_fraction * max(available, debited.value)
            ):
                continue

            now = transfer.close_time
            route = (transfer.destination, transfer.destination_tag, debited.asset)
            forwards = routes[route]
            while forwards and now - forwards[0].transfer.close_time > settings.funnel_window:
                forwards.popleft()
            forwards.append(_Forward(transfer, forwarded, hashes))
            senders = {forward.transfer.source for forward in forwards}
            if len(senders) < settings.funnel_min_senders:
                continue
            if route in last_alert and now - last_alert[route] <= settings.funnel_window:
                continue

            last_alert[route] = now
            evidence = tuple(
                dict.fromkeys(
                    tx_hash
                    for forward in forwards
                    for tx_hash in (*forward.incoming_hashes, forward.transfer.tx_hash)
                )
            )
            destination = transfer.destination
            if transfer.destination_tag is not None:
                destination = f"{destination}:{transfer.destination_tag}"
            findings.append(
                Finding(
                    FindingKind.FUNDS_FUNNEL,
                    destination,
                    debited.asset,
                    transfer_point(transfer),
                    evidence,
                    (
                        ("sender_count", len(senders)),
                        ("matched_inflow_upper_bound", sum(forward.amount for forward in forwards)),
                    ),
                )
            )

        # Credits become available for matching only after this transaction's debits.
        for transfer in transaction:
            if (
                transfer.kind == TransferKind.PAYMENT
                and transfer.source != transfer.destination
                and transfer.amount.value > 0
            ):
                credits[transfer.destination, transfer.amount.asset].append(
                    _Credit(transfer.close_time, transfer.tx_hash, transfer.amount.value)
                )
    return findings


@dataclass
class _Outflows:
    starting_balance: Decimal
    total: Decimal = Decimal(0)
    hashes: list[str] = field(default_factory=list)
    destinations: set[tuple[str, int | None]] = field(default_factory=set)


def _wallet_takeovers(
    events: list[SigningChange | Transfer],
    previously_known: set[tuple[str, int | None]],
    balances: dict[tuple[str, str, Asset], Decimal],
    settings: DetectionSettings,
) -> list[Finding]:
    findings: list[Finding] = []
    active_change: SigningChange | None = None
    known_at_change = frozenset(previously_known)
    outflows: dict[Asset, _Outflows] = {}
    for event in sorted(events, key=lambda item: item.order_key):
        if isinstance(event, SigningChange):
            active_change = event
            known_at_change = frozenset(previously_known)
            outflows.clear()
            continue

        destination = event.destination, event.destination_tag
        previously_known.add(destination)
        if active_change is None or event.order_key <= active_change.order_key:
            continue
        if event.close_time - active_change.event.close_time > settings.takeover_window:
            active_change = None
            continue
        if destination in known_at_change:
            continue

        debited = event.source_amount or event.amount
        asset = debited.asset
        if asset not in outflows:
            starting = balances.get((event.tx_hash, event.source, asset))
            if starting is None or starting <= 0:
                continue
            outflows[asset] = _Outflows(starting)
        evidence = outflows[asset]
        evidence.total += debited.value
        evidence.hashes.append(event.tx_hash)
        evidence.destinations.add(destination)
        fraction = evidence.total / evidence.starting_balance
        if fraction >= settings.takeover_min_outflow:
            findings.append(
                Finding(
                    FindingKind.POSSIBLE_TAKEOVER,
                    event.source,
                    asset,
                    transfer_point(event),
                    tuple(dict.fromkeys((active_change.event.tx_hash, *evidence.hashes))),
                    (
                        ("signing_change", active_change.event.kind.value),
                        ("new_destination_count", len(evidence.destinations)),
                        ("outflow_fraction_of_starting_balance", fraction),
                    ),
                )
            )
            active_change = None
    return findings


def detect_takeovers(
    batch: DetectionBatch, settings: DetectionSettings, transfers: Sequence[Transfer]
) -> list[Finding]:
    """Look for rapid, substantial novel-destination debits after a signing change."""
    events: defaultdict[str, list[SigningChange | Transfer]] = defaultdict(list)
    known: defaultdict[str, set[tuple[str, int | None]]] = defaultdict(set)
    for change in dict.fromkeys(batch.signing_changes):
        if change.event.kind != SecurityEventKind.ACCOUNT_DELETE:
            events[change.event.account].append(change)
    for transfer in transfers:
        if (
            transfer.source in events
            and transfer.source != transfer.destination
            and (transfer.source_amount or transfer.amount).value > 0
        ):
            events[transfer.source].append(transfer)
    for source, destination, tag in batch.known_destinations:
        known[source].add((destination, tag))
    balances = {
        (
            observation.tx_hash,
            observation.account,
            observation.amount.asset,
        ): observation.amount.value
        for observation in batch.balances_before
    }
    return [
        finding
        for wallet, wallet_events in events.items()
        for finding in _wallet_takeovers(wallet_events, known[wallet], balances, settings)
    ]
