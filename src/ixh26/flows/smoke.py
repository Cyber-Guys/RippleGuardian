"""``make smoke``: the demo path offline, on a SIMULATED theft (no network, in-memory DB).

# SIMULATED: every address, hash and amount below is synthetic test input. It is never shown
# in the UI or used as evidence; the real demo (scripts/demo.py) runs on Testnet.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ixh26 import config
from ixh26.contracts import (
    XRP,
    AccountActivity,
    AccountLabel,
    AccountLabelKind,
    Amount,
    PreTxBalance,
    SecurityEvent,
    SecurityEventKind,
    TraceParams,
    Transfer,
    TransferKind,
)
from ixh26.flows.monitor import Monitor
from ixh26.flows.trace import alert_victims, build_trace
from ixh26.store.repo import Store

log = logging.getLogger(__name__)

XRP1 = Decimal(1_000_000)
VICTIM, ATTACKER, EXCHANGE = "rSIMULATEDVictim", "rSIMULATEDAttacker", "rSIMULATEDExchange"
MULES = ("rSIMULATEDMule1", "rSIMULATEDMule2", "rSIMULATEDMule3")
TAG = 777
START = datetime(2026, 11, 21, 1, 0, tzinfo=UTC)
OPENING = {VICTIM: 100 * XRP1}


def _hash(n: int) -> str:
    return f"{n:064X}"


def _pay(n: int, src: str, dst: str, xrp: int, tag: int | None = None) -> AccountActivity:
    t = Transfer(
        _hash(n),
        1000 + n,
        0,
        START + timedelta(seconds=4 * n),
        TransferKind.PAYMENT,
        src,
        dst,
        Amount(XRP, xrp * XRP1),
        destination_tag=tag,
    )
    return AccountActivity(transfers=(t,))


def scenario() -> list[AccountActivity]:
    """Victim's key is replaced, funds are split across mules and funnelled to one exchange."""
    rekey = SecurityEvent(
        _hash(1),
        1001,
        START + timedelta(seconds=4),
        VICTIM,
        SecurityEventKind.SET_REGULAR_KEY,
        ATTACKER,
    )
    drain = _pay(2, VICTIM, ATTACKER, 95)
    drain = AccountActivity(
        drain.transfers, (), (PreTxBalance(_hash(2), VICTIM, Amount(XRP, 100 * XRP1)),)
    )
    return [
        AccountActivity(security_events=(rekey,)),
        drain,
        _pay(3, ATTACKER, MULES[0], 40),
        _pay(4, ATTACKER, MULES[1], 30),
        _pay(5, ATTACKER, MULES[2], 25),
        _pay(6, MULES[0], EXCHANGE, 40, TAG),
        _pay(7, MULES[1], EXCHANGE, 30, TAG),
        _pay(8, MULES[2], EXCHANGE, 25, TAG),
    ]


class FakeReader:
    """SIMULATED ledger: serves ``scenario()`` per account, like account_tx would."""

    def __init__(self, activities: Sequence[AccountActivity]) -> None:
        self._activities = list(activities)

    async def account_activity(
        self, account: str, *, from_ledger: int, to_ledger: int | None = None
    ) -> list[AccountActivity]:
        def involved(a: AccountActivity) -> bool:
            return any(account in (t.source, t.destination) for t in a.transfers) or any(
                e.account == account for e in a.security_events
            )

        def ledger(a: AccountActivity) -> int:
            return (a.transfers or a.security_events)[0].ledger_index

        return [
            a
            for a in self._activities
            if involved(a)
            and ledger(a) >= from_ledger
            and (to_ledger is None or ledger(a) <= to_ledger)
        ]

    async def xrp_balance(self, account: str, ledger_index: int | str = "validated") -> Decimal:
        return OPENING.get(account, Decimal(0))


async def run_scenario(store: Store) -> dict[str, object]:
    """Victim watched by user ``demo``: live alerts, detector findings, trace to the exchange."""
    user = store.create_user("demo", "not-a-real-hash")
    store.add_wallet(user.id, VICTIM, "Savings (SIMULATED)")
    store.set_cursor(VICTIM, 1000)
    store.upsert_label(AccountLabel(EXCHANGE, AccountLabelKind.EXCHANGE, "Exchange (SIMULATED)"))
    monitor = Monitor(store)
    reader = FakeReader(scenario())
    for activity in await reader.account_activity(VICTIM, from_ledger=1001):
        monitor.process(activity)
    params = TraceParams(VICTIM, XRP, 95 * XRP1, start_ledger=1001)
    result, _ = await build_trace(reader, monitor, params)
    alert_victims(store, result)
    return {
        "alerts": [a.kind for a in store.alerts(user.id)],
        "findings": sorted(f.kind for f in store.findings()),
        "sinks": [(s.address, s.destination_tag, s.taint_value) for s in result.sinks],
    }


def run(settings: config.Settings) -> int:
    import asyncio

    outcome = asyncio.run(run_scenario(Store.from_url("sqlite://")))
    expected_sink = (EXCHANGE, TAG, 95 * XRP1)
    checks = {
        "security alert": "security_change" in outcome["alerts"],
        "outgoing alert": "outgoing_payment" in outcome["alerts"],
        "exchange alert": "taint_at_exchange" in outcome["alerts"],
        "takeover finding": "possible_takeover" in outcome["findings"],
        "funnel finding": "funds_funnel" in outcome["findings"],
        "trace reaches exchange+tag": outcome["sinks"] == [expected_sink],
    }
    for name, ok in checks.items():
        log.info("smoke %-28s %s", name, "ok" if ok else "FAILED")
    if not all(checks.values()):
        raise SystemExit(f"smoke failed: {outcome}")
    log.info("smoke ok (SIMULATED scenario, network=%s untouched)", settings.network.name)
    return 0
