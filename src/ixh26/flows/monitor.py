"""New ledger activity -> stored history, in-app alerts for owners, detector findings.

activity --save--> store --alerts_for--> wants(wallet)? --> store.add_alert
                         \\--run_detectors--> store.add_finding (analysts only)
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import AccountActivity, Alert, AlertKind, SecurityEvent, Transfer
from ixh26.core.alerts import FlagNote, alerts_for
from ixh26.core.detection import (
    BalanceBefore,
    DetectionBatch,
    DetectionSettings,
    Finding,
    SigningChange,
    detect,
)
from ixh26.flows.detection_settings import effective_detection_settings
from ixh26.store.models import Wallet
from ixh26.store.repo import FindingInput, Store

log = logging.getLogger(__name__)


def wants(wallet: Wallet, alert: Alert, drops: Decimal | None) -> bool:
    """Does this owner want this alert, given their per-wallet settings?"""
    if alert.kind is AlertKind.SECURITY_CHANGE:
        return wallet.notify_security
    if alert.kind is AlertKind.FLAGGED_COUNTERPARTY:
        return wallet.notify_flagged
    if alert.kind is AlertKind.OUTGOING_PAYMENT:
        above_threshold = drops is None or drops >= Decimal(wallet.min_outgoing_drops)
        return wallet.notify_outgoing and above_threshold
    return True


def xrp_drops(transfers: Iterable[Transfer]) -> dict[str, Decimal]:
    """tx hash -> XRP amount in drops, for the outgoing-payment threshold."""
    return {t.tx_hash: t.amount.value for t in transfers if t.amount.asset.is_xrp}


def flag_notes(store: Store) -> dict[str, FlagNote]:
    return {target: FlagNote(f.category, f.reason) for target, f in store.flagged_targets().items()}


def to_finding_input(f: Finding) -> FindingInput:
    return FindingInput(
        kind=f.kind.value,
        subject=f.subject,
        asset=str(f.asset),
        tx_hash=f.trigger.tx_hash,
        ledger_index=f.trigger.ledger_index,
        close_time=f.trigger.close_time,
        evidence=f.evidence_hashes,
        metrics={k: str(v) for k, v in f.metrics},
    )


def detection_batch(store: Store, accounts: list[str]) -> DetectionBatch:
    """Everything the detectors need about ``accounts``, from stored history."""
    transfers = store.transfers_of(accounts)
    events = store.events_of(accounts)
    balances = store.balances_for({t.tx_hash for t in transfers})
    return DetectionBatch(
        transfers=tuple(transfers),
        signing_changes=tuple(SigningChange(e, e.tx_index) for e in events),
        balances_before=tuple(BalanceBefore(b.tx_hash, b.account, b.amount) for b in balances),
        # shortcut: DEX fills and AMM withdrawals are not normalised yet, so the wash-trading
        # and liquidity-drop detectors only see data supplied by tests (roadmap)
    )


@dataclass
class Monitor:
    store: Store
    detection: DetectionSettings | None = None

    def process(self, activity: AccountActivity, *, notify: bool = True) -> list[Alert]:
        """Store ``activity``; alert watchers about what is new; run the detectors."""
        transfers, events = self.store.save_activity(activity)
        if not (transfers or events):
            return []
        delivered = self.deliver(transfers, events) if notify else []
        self.run_detectors({t.source for t in transfers} | {e.account for e in events})
        return delivered

    def deliver(self, transfers: list[Transfer], events: list[SecurityEvent]) -> list[Alert]:
        """Store each alert for every watcher who wants it; return the alerts sent."""
        now = datetime.now(UTC)
        drops = xrp_drops(transfers)
        sent = []
        for alert in alerts_for(transfers, events, flag_notes(self.store), now):
            amount = drops.get(alert.tx_hash) if alert.kind is AlertKind.OUTGOING_PAYMENT else None
            receivers = [w for w in self.store.watchers(alert.wallet) if wants(w, alert, amount)]
            if any([self.store.add_alert(w.user_id, alert) for w in receivers]):
                sent.append(alert)
        return sent

    def run_detectors(self, accounts: Iterable[str]) -> list[Finding]:
        """Run every detector over the stored history of ``accounts``; keep new findings."""
        accounts = sorted(set(accounts))
        if not accounts:
            return []
        settings = (
            self.detection
            if self.detection is not None
            else effective_detection_settings(self.store)
        )
        findings = detect(detection_batch(self.store, accounts), settings)
        new = [f for f in findings if self.store.add_finding(to_finding_input(f))]
        for f in new:
            log.info("finding %s on %s (tx %s)", f.kind.value, f.subject, f.trigger.tx_hash)
        return new
