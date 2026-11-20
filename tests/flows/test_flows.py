from decimal import Decimal
from pathlib import Path

import pytest

from ixh26 import config
from ixh26.contracts import XRP, AlertKind
from ixh26.flows import smoke
from ixh26.flows.monitor import Monitor
from ixh26.flows.trace import run_trace_job
from ixh26.flows.worker import catch_up
from ixh26.store.repo import Store

SETTINGS = config.load_settings({})


async def test_demo_path_alerts_findings_and_trace() -> None:
    outcome = await smoke.run_scenario(Store.from_url("sqlite://"))
    assert {"security_change", "outgoing_payment", "taint_at_exchange"} <= set(outcome["alerts"])
    assert outcome["findings"] == ["funds_funnel", "possible_takeover"]
    assert outcome["sinks"] == [(smoke.EXCHANGE, smoke.TAG, 95 * smoke.XRP1)]


def test_flagged_counterparty_and_per_wallet_settings() -> None:
    store = Store.from_url("sqlite://")
    ana = store.create_user("ana", "h", role="analyst")
    alice = store.create_user("alice", "h")
    store.add_wallet(alice.id, smoke.MULES[0])
    store.add_flag("account", smoke.EXCHANGE, "theft", "receives stolen funds", ana.id)
    store.update_wallet(alice.id, smoke.MULES[0], min_outgoing_drops=str(100 * smoke.XRP1))
    Monitor(store).process(smoke._pay(6, smoke.MULES[0], smoke.EXCHANGE, 40, smoke.TAG))
    kinds = [a.kind for a in store.alerts(alice.id)]
    assert kinds == [AlertKind.FLAGGED_COUNTERPARTY.value]  # 40 XRP is below the 100 XRP threshold


def test_flag_alert_can_be_disabled() -> None:
    store = Store.from_url("sqlite://")
    ana = store.create_user("ana", "h", role="analyst")
    bob = store.create_user("bob", "h")
    store.add_wallet(bob.id, smoke.EXCHANGE)
    store.update_wallet(bob.id, smoke.EXCHANGE, notify_flagged=False)
    store.add_flag("account", smoke.MULES[1], "scam", "mule", ana.id)
    Monitor(store).process(smoke._pay(7, smoke.MULES[1], smoke.EXCHANGE, 30, smoke.TAG))
    assert store.alerts(bob.id) == []


class CatchUpReader(smoke.FakeReader):
    def __init__(self) -> None:
        super().__init__(smoke.scenario())
        self.ledger = 1003

    async def current_ledger(self) -> int:
        return self.ledger


async def test_polling_backfills_silently_then_catches_up_with_alerts() -> None:
    store = Store.from_url("sqlite://")
    user = store.create_user("demo", "h")
    store.add_wallet(user.id, smoke.ATTACKER)
    reader = CatchUpReader()
    monitor = Monitor(store)
    await catch_up(reader, monitor)  # first sight: history only, no alerts
    assert store.alerts(user.id) == [] and store.cursor(smoke.ATTACKER) == 1003
    reader.ledger = 1008  # e.g. after a WebSocket disconnect
    await catch_up(reader, monitor)
    assert len(store.alerts(user.id)) == 2  # payments to Mule2 and Mule3 (ledgers 1004, 1005)


async def test_trace_job_stores_graph_or_error() -> None:
    store = Store.from_url("sqlite://")
    ana = store.create_user("ana", "h", role="analyst")
    row = store.create_trace(ana.id, smoke.VICTIM, XRP, Decimal(95 * smoke.XRP1), 1001)
    await run_trace_job(smoke.FakeReader(smoke.scenario()), Monitor(store), row, SETTINGS)
    done = store.trace(row.id)
    assert done.status == "done"
    assert [e["hop"] for e in done.result["edges"]] == [1, 2, 2, 2, 3, 3, 3]

    class Broken(smoke.FakeReader):
        async def account_activity(self, *a: object, **k: object) -> list:
            raise RuntimeError("endpoint down")

    bad = store.create_trace(ana.id, smoke.VICTIM, XRP, Decimal(1), 1)
    await run_trace_job(Broken([]), Monitor(store), bad, SETTINGS)
    assert store.trace(bad.id).status == "failed"
    assert "endpoint down" in store.trace(bad.id).error


def test_cli_creates_analyst_and_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from ixh26.cli import main

    db = f"sqlite:///{tmp_path}/cli.db"
    monkeypatch.setenv("DATABASE_URL", db)
    monkeypatch.setattr("sys.stdin", io.StringIO("analyst-password\n"))
    assert main(["create-user", "ana", "--role", "analyst", "--password-stdin"]) == 0
    assert main(["label", smoke.EXCHANGE, "--name", "Exchange"]) == 0
    store = Store.from_url(db)
    assert store.user_by_name("ana").role == "analyst"
    assert smoke.EXCHANGE in store.labels()
