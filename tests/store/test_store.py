from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import (
    XRP,
    AccountActivity,
    Alert,
    AlertKind,
    AlertSeverity,
    Amount,
    PreTxBalance,
    Transfer,
    TransferKind,
)
from ixh26.store.repo import FindingInput, Store

NOW = datetime(2026, 11, 20, 23, 0, tzinfo=UTC)


def _transfer(n: int) -> Transfer:
    return Transfer(
        f"{n:064X}", 100 + n, 0, NOW, TransferKind.PAYMENT, "rA", "rB", Amount(XRP, Decimal(n))
    )


def test_activity_is_idempotent_and_round_trips() -> None:
    store = Store.from_url("sqlite://")
    activity = AccountActivity(
        transfers=(_transfer(1),),
        pre_tx_balances=(PreTxBalance(_transfer(1).tx_hash, "rA", Amount(XRP, Decimal(9))),),
    )
    assert store.save_activity(activity)[0] == [_transfer(1)]
    assert store.save_activity(activity)[0] == []
    assert store.transfers_of(["rB"]) == [_transfer(1)]
    assert store.balances_for([_transfer(1).tx_hash])[0].amount.value == Decimal(9)


def test_alerts_are_per_user_and_deduplicated() -> None:
    store = Store.from_url("sqlite://")
    alice = store.create_user("alice", "h")
    bob = store.create_user("bob", "h")
    alert = Alert("rA", AlertKind.OUTGOING_PAYMENT, AlertSeverity.WARNING, "F" * 64, "m", NOW)
    assert store.add_alert(alice.id, alert) is True
    assert store.add_alert(alice.id, alert) is False
    assert store.unread_count(alice.id) == 1 and store.unread_count(bob.id) == 0
    store.mark_read(alice.id)
    assert store.unread_count(alice.id) == 0


def test_findings_flags_and_traces() -> None:
    store = Store.from_url("sqlite://")
    analyst = store.create_user("ana", "h", role="analyst")
    finding = FindingInput("possible_takeover", "rA", "XRP", "E" * 64, 5, NOW, ("E" * 64,), {})
    assert store.add_finding(finding) and not store.add_finding(finding)
    (row,) = store.findings("open")
    flag = store.add_flag("account", "rA", "theft", "drained", analyst.id, row.id)
    assert store.flagged_targets()["rA"].id == flag.id
    store.revoke_flag(flag.id)
    assert store.flagged_targets() == {}
    trace = store.create_trace(analyst.id, "rA", XRP, Decimal(10), 1)
    assert [t.id for t in store.pending_traces()] == [trace.id]
    store.finish_trace(trace.id, result={"edges": []})
    assert store.trace(trace.id).status == "done"
