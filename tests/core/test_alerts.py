from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import (
    XRP,
    AlertKind,
    Amount,
    SecurityEvent,
    SecurityEventKind,
    Transfer,
    TransferKind,
)
from ixh26.core.alerts import FlagNote, alerts_for, amount_text, flagged_contact_alerts

NOW = datetime(2026, 11, 21, tzinfo=UTC)
PAY = Transfer(
    "AB" * 32,
    1,
    0,
    NOW,
    TransferKind.PAYMENT,
    "rAlice",
    "rMallory",
    Amount(XRP, Decimal(2_500_000)),
)


def test_amount_text_shows_xrp_not_drops() -> None:
    assert amount_text(PAY.amount) == "2.5 XRP"


def test_flagged_counterparty_warns_the_side_that_touched_it() -> None:
    (alert,) = flagged_contact_alerts(PAY, {"rMallory": FlagNote("theft", "drainer")}, NOW)
    assert alert.wallet == "rAlice" and alert.kind is AlertKind.FLAGGED_COUNTERPARTY
    assert "theft: drainer" in alert.message


def test_new_activity_yields_security_and_outgoing_alerts() -> None:
    rekey = SecurityEvent("CD" * 32, 1, NOW, "rAlice", SecurityEventKind.SET_REGULAR_KEY, "rK")
    kinds = [a.kind for a in alerts_for([PAY], [rekey], {}, NOW)]
    assert kinds == [AlertKind.SECURITY_CHANGE, AlertKind.OUTGOING_PAYMENT]
