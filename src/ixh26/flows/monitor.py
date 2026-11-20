"""Ledger activity -> stored history, in-app alerts for wallet owners, detector findings."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import (
    AccountActivity,
    Alert,
    AlertKind,
    AlertSeverity,
    Amount,
    SecurityEvent,
    Transfer,
)
from ixh26.core.detection import (
    BalanceBefore,
    DetectionBatch,
    DetectionSettings,
    Finding,
    SigningChange,
    detect,
)
from ixh26.store.models import FlagRow
from ixh26.store.repo import FindingInput, Store

log = logging.getLogger(__name__)


def fmt_amount(amount: Amount) -> str:
    if amount.asset.is_xrp:
        return f"{(amount.value / 1_000_000).normalize():f} XRP"
    return f"{amount.value.normalize():f} {amount.asset.currency}"


def short(address: str) -> str:
    return f"{address[:6]}…{address[-4:]}"


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


@dataclass
class Monitor:
    store: Store
    detection: DetectionSettings = field(default_factory=DetectionSettings)

    def process(self, activity: AccountActivity, *, notify: bool = True) -> list[Alert]:
        """Store ``activity``; alert watchers about what is new; run the detectors."""
        new_t, new_e = self.store.save_activity(activity)
        if not (new_t or new_e):
            return []
        alerts = self._notify(new_t, new_e) if notify else []
        accounts = {t.source for t in new_t} | {e.account for e in new_e}
        self.run_detectors(accounts)
        return alerts

    # --- notifications (users) ----------------------------------------------------------------

    def _emit(self, address: str, alert: Alert, drops: Decimal | None) -> bool:
        """Store ``alert`` for every watcher of ``address`` whose settings allow it."""
        sent = False
        for wallet in self.store.watchers(address):
            enabled = {
                AlertKind.OUTGOING_PAYMENT: wallet.notify_outgoing,
                AlertKind.SECURITY_CHANGE: wallet.notify_security,
                AlertKind.FLAGGED_COUNTERPARTY: wallet.notify_flagged,
            }.get(alert.kind, True)
            if drops is not None:  # XRP outgoing payments honour the per-wallet threshold
                enabled = enabled and drops >= Decimal(wallet.min_outgoing_drops)
            if enabled:
                sent |= self.store.add_alert(wallet.user_id, alert)
        return sent

    def _notify(
        self, transfers: Sequence[Transfer], events: Sequence[SecurityEvent]
    ) -> list[Alert]:
        now = datetime.now(UTC)
        flagged = self.store.flagged_targets()
        out: list[Alert] = []

        def emit(address: str, alert: Alert, drops: Decimal | None = None) -> None:
            if self._emit(address, alert, drops):
                out.append(alert)

        for e in events:
            emit(
                e.account,
                Alert(
                    e.account,
                    AlertKind.SECURITY_CHANGE,
                    AlertSeverity.CRITICAL,
                    e.tx_hash,
                    f"Signing configuration changed: {e.kind.value.replace('_', ' ')}"
                    + (f" ({e.detail})" if e.detail else "")
                    + ". If this wasn't you, your keys may be compromised.",
                    now,
                ),
            )
        for t in transfers:
            tag = f" (tag {t.destination_tag})" if t.destination_tag is not None else ""
            drops = t.amount.value if t.amount.asset.is_xrp else None
            emit(
                t.source,
                Alert(
                    t.source,
                    AlertKind.OUTGOING_PAYMENT,
                    AlertSeverity.WARNING,
                    t.tx_hash,
                    f"Sent {fmt_amount(t.amount)} to {short(t.destination)}{tag}.",
                    now,
                ),
                drops,
            )
            for alert_wallet, other, direction in (
                (t.source, t.destination, "Sent funds to"),
                (t.destination, t.source, "Received funds from"),
            ):
                flag: FlagRow | None = flagged.get(other) or flagged.get(t.tx_hash.upper())
                if flag is not None:
                    emit(
                        alert_wallet,
                        Alert(
                            alert_wallet,
                            AlertKind.FLAGGED_COUNTERPARTY,
                            AlertSeverity.CRITICAL,
                            t.tx_hash,
                            f"{direction} {short(other)}, flagged by an analyst as "
                            f"{flag.category}: {flag.reason}",
                            now,
                        ),
                    )
        return out

    # --- detection (analysts) -----------------------------------------------------------------

    def run_detectors(self, accounts: Iterable[str]) -> list[Finding]:
        """Run every detector over the stored history of ``accounts``; store new findings."""
        accounts = sorted(set(accounts))
        if not accounts:
            return []
        transfers = self.store.transfers_of(accounts)
        events = self.store.events_of(accounts)
        balances = self.store.balances_for({t.tx_hash for t in transfers})
        batch = DetectionBatch(
            transfers=tuple(transfers),
            signing_changes=tuple(SigningChange(e, e.tx_index) for e in events),
            balances_before=tuple(BalanceBefore(b.tx_hash, b.account, b.amount) for b in balances),
            # shortcut: no DEX fills / AMM withdrawals are normalised yet, so the wash-trading
            # and liquidity-drop detectors only run on data supplied by tests (roadmap)
        )
        findings = detect(batch, self.detection)
        new = [f for f in findings if self.store.add_finding(to_finding_input(f))]
        for f in new:
            log.info("finding %s on %s (tx %s)", f.kind.value, f.subject, f.trigger.tx_hash)
        return new
