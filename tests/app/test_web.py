import re
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from ixh26 import config
from ixh26.app.auth import hash_password
from ixh26.app.main import create_app
from ixh26.contracts import XRP
from ixh26.flows import smoke
from ixh26.flows.monitor import Monitor
from ixh26.flows.trace import run_trace_job
from ixh26.store.repo import Store

SETTINGS = config.load_settings({})


@pytest.fixture
async def store() -> Store:
    """SIMULATED scenario from flows/smoke.py: victim watched by 'demo', findings, labels."""
    store = Store.from_url("sqlite://")
    await smoke.run_scenario(store)
    ana = store.create_user("ana", hash_password("analyst-pass"), role="analyst")
    store.create_user("carol", hash_password("carol-pass"))
    row = store.create_trace(ana.id, smoke.VICTIM, XRP, Decimal(95 * smoke.XRP1), 1001)
    await run_trace_job(smoke.FakeReader(smoke.scenario()), Monitor(store), row, SETTINGS)
    return store


def client_for(store: Store, username: str, password: str) -> TestClient:
    client = TestClient(create_app(SETTINGS, store))
    r = client.post("/login", data={"username": username, "password": password})
    assert r.status_code == 200 and r.url.path != "/login", r.text[:300]
    return client


def test_anonymous_is_sent_to_login(store: Store) -> None:
    r = TestClient(create_app(SETTINGS, store)).get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_register_then_watch_wallet_and_see_statement(store: Store) -> None:
    client = TestClient(create_app(SETTINGS, store))
    r = client.post("/register", data={"username": "dave", "password": "dave-pass-1"})
    assert "Your wallets" in r.text
    r = client.post("/wallets", data={"address": "nope"})
    assert "not a valid XRPL address" in r.text
    r = client.post(
        "/wallets", data={"address": "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY", "label": "Mine"}
    )
    assert r.status_code == 200 and "Mine" in r.text


def test_user_pages_and_role_enforcement(store: Store) -> None:
    demo = store.user_by_name("demo")
    client = TestClient(create_app(SETTINGS, store))
    with store.session() as s:  # give the SIMULATED demo user a usable password
        s.get(type(demo), demo.id).password_hash = hash_password("demo-pass")
    client = client_for(store, "demo", "demo-pass")
    home = client.get("/")
    assert (
        "Savings (SIMULATED) may be compromised" in home.text and "What to do now" in home.text
    )  # unread security alert on the victim
    wallet = client.get(f"/wallets/{smoke.VICTIM}")
    assert (
        wallet.status_code == 200
        and "Balance from recorded transfers" in wallet.text
        and "<svg" in wallet.text
    )
    assert client.get("/notifications").status_code == 200
    assert re.search(r'class="count"[^>]*>\s*\d', client.get("/ui/unread").text)
    assert client.get("/analyst/findings").status_code == 403
    assert client.post("/flags", data={"target": smoke.VICTIM, "reason": "nope"}).status_code == 403
    r = client.post(f"/wallets/{smoke.VICTIM}/settings", data={"min_outgoing_xrp": "5"})
    assert "Settings saved" in r.text


def test_analyst_findings_trace_and_flag_visible_to_users(store: Store) -> None:
    ana = client_for(store, "ana", "analyst-pass")
    overview = ana.get("/analyst")
    assert "Open findings" in overview.text and 'class="flow-band"' in overview.text
    findings = ana.get("/analyst/findings")
    assert "Possible takeover" in findings.text and "Funds funnel" in findings.text
    trace = ana.get("/analyst/traces/1")
    assert "Where the stolen funds went" in trace.text
    assert "Exchange (SIMULATED)" in trace.text and "tag 777" in trace.text
    r = ana.post(
        "/flags",
        data={
            "target": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
            "reason": "received drained funds",
            "category": "theft",
        },
    )
    assert r.status_code == 200
    carol = client_for(store, "carol", "carol-pass")
    lookup = carol.get("/flags", params={"q": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"})
    assert "Flagged as theft" in lookup.text and "ana" in lookup.text


def test_flow_marks_only_stops_and_known_entities() -> None:
    from ixh26.app.charts import flow_graph, flow_nodes

    edge = {
        "destination_tag": None,
        "taint": "5 XRP",
        "taint_value": "5000000",
        "tx_hash": "AB" * 32,
    }
    report = {
        "params": {"origin": "rVictim", "stolen": "10 XRP", "stolen_value": "10000000"},
        "edges": [
            {**edge, "hop": 1, "source": "rVictim", "destination": "rMule"},
            {**edge, "hop": 2, "source": "rMule", "destination": "rEx", "destination_tag": 7},
            {**edge, "hop": 1, "source": "rVictim", "destination": "rStay"},
        ],
        "sinks": [
            {"address": "rEx", "destination_tag": 7, "label": "Exchange"},
            {"address": "rMule", "destination_tag": None, "label": None},  # reserve left behind
            {"address": "rStay", "destination_tag": None, "label": None},
        ],
    }
    kinds = {n.key[0]: n.kind for n in flow_nodes(report)}
    assert kinds == {"rVictim": "origin", "rMule": "hop", "rEx": "sink", "rStay": "sink"}
    svg = str(flow_graph(report))
    assert svg.count('class="flow-band"') == 3 and "Exchange, tag 7" in svg


def test_balance_line_follows_transfers() -> None:
    from datetime import UTC, datetime
    from decimal import Decimal

    from ixh26.app.charts import line_chart
    from ixh26.app.views.models import balance_points
    from ixh26.contracts import XRP, Amount, Transfer, TransferKind

    t0 = datetime(2026, 11, 21, tzinfo=UTC)

    def pay(n: int, src: str, dst: str, xrp: int) -> Transfer:
        return Transfer(
            f"{n:064X}",
            n,
            0,
            t0.replace(minute=n),
            TransferKind.PAYMENT,
            src,
            dst,
            Amount(XRP, Decimal(xrp * 1_000_000)),
        )

    points = balance_points("rMe", [pay(1, "rFaucet", "rMe", 100), pay(2, "rMe", "rThief", 99)])
    assert [p.value for p in points] == [Decimal(100), Decimal(1)]
    assert "<svg" in str(line_chart(points, unit="XRP"))
