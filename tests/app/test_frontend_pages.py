"""HTML pages for detector settings, transaction search and wallet verification."""

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from xrpl.models import Response
from xrpl.models.requests import AccountInfo, Ledger, Request, Tx
from xrpl.models.response import ResponseStatus

from ixh26 import config
from ixh26.app.auth import hash_password
from ixh26.app.main import create_app
from ixh26.app.views import lookup_pages
from ixh26.flows.transactions import LedgerError, TransactionNotFound, TransactionNotValidated
from ixh26.ledger import client as ledger
from ixh26.store.models import WalletChallenge, utcnow
from ixh26.store.repo import Store

SETTINGS = config.load_settings({})
SOURCE = "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY"
RECIPIENT = "rDsbeomae4FXwgQTJp9Rs64Qg9vDiTCdBv"
HASH = "A3" * 32


def make_client(store: Store, username: str) -> TestClient:
    client = TestClient(create_app(SETTINGS, store))
    r = client.post("/login", data={"username": username, "password": "testing-123"})
    assert r.status_code == 200 and r.url.path != "/login"
    return client


@pytest.fixture
def store() -> Store:
    store = Store.from_url("sqlite://")
    store.create_user("ana", hash_password("testing-123"), role="analyst")
    store.create_user("ben", hash_password("testing-123"), role="analyst")
    for name in ("alice", "bruno"):
        user = store.create_user(name, hash_password("testing-123"))
        store.add_wallet(user.id, SOURCE, "Savings")
    return store


# --- A. detector settings ------------------------------------------------------------------


def test_settings_page_is_analyst_only_and_grouped(store: Store) -> None:
    assert make_client(store, "alice").get("/analyst/settings").status_code == 403
    anon = TestClient(create_app(SETTINGS, store))
    assert anon.get("/analyst/settings", follow_redirects=False).status_code == 303
    page = make_client(store, "ana").get("/analyst/settings").text
    for group in ("Funds funnel", "Wash trading", "Liquidity withdrawal", "Wallet takeover"):
        assert group in page
    assert page.count("Live data unavailable") == 2 and page.count("Live on the worker") == 2
    assert "Factory defaults" in page and "drops (1 XRP = 1,000,000)" in page
    assert 'name="funnel_window_seconds" type="text" inputmode="decimal" value="1800"' in page


def form_values(client: TestClient) -> dict[str, str]:
    import re

    html = client.get("/analyst/settings").text
    values = dict(re.findall(r'name="(\w+)" type="text"[^>]*value="([^"]*)"', html))
    values["version"] = re.search(r'name="version" value="(\d+)"', html).group(1)
    return values


def test_settings_save_persist_restore_errors_and_conflict(store: Store) -> None:
    ana, ben = make_client(store, "ana"), make_client(store, "ben")
    values = form_values(ana)
    r = ana.post("/analyst/settings", data={**values, "funnel_min_senders": "4"})
    assert "Saved" in r.text
    again = form_values(ana)
    assert again["funnel_min_senders"] == "4" and again["version"] == "1"

    bad = ana.post("/analyst/settings", data={**again, "takeover_min_outflow": "1.5"})
    assert bad.status_code == 422 and "Fix the highlighted fields" in bad.text
    assert 'value="1.5"' in bad.text  # the draft is preserved
    assert (
        ana.post("/analyst/settings", data={**again, "funnel_window_seconds": "x"}).status_code
        == 422
    )

    ben_values = form_values(ben)  # ben reads version 1, ana saves version 2 first
    ana.post("/analyst/settings", data={**again, "funnel_min_senders": "5"})
    stale = ben.post("/analyst/settings", data={**ben_values, "funnel_min_senders": "6"})
    assert stale.status_code == 409 and "Another analyst saved newer settings" in stale.text
    assert "Latest saved: <strong>5</strong>" in stale.text and 'value="6"' in stale.text

    restored = ana.post("/analyst/settings/restore", data={"version": "2"})
    assert "Saved" in restored.text
    final = form_values(ana)
    assert final["funnel_min_senders"] == "3" and final["version"] == "3"


# --- B. transaction search -----------------------------------------------------------------


def found(network: str, result: str = "tesSUCCESS") -> dict[str, Any]:
    return {
        "network": network,
        "hash": HASH,
        "ledger_index": 700,
        "validated": True,
        "result": result,
        "transaction": {"TransactionType": "Payment", "Account": SOURCE, "Destination": RECIPIENT},
        "metadata": {"TransactionResult": result},
        "explorer_url": f"https://example.test/{HASH}",
    }


def test_lookup_uses_the_selected_network_only_for_the_search(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    async def fake(endpoints: config.NetworkEndpoints, tx_hash: str) -> dict[str, Any]:
        seen.append(endpoints.name)
        return found(
            endpoints.name, "tecUNFUNDED_PAYMENT" if tx_hash.startswith("B4") else "tesSUCCESS"
        )

    monkeypatch.setattr(lookup_pages, "lookup_transaction", fake)
    client = make_client(store, "alice")
    ok = client.get("/transactions", params={"hash": HASH, "network": "mainnet"})
    assert "Mainnet transaction" in ok.text and "Succeeded" in ok.text and seen == ["mainnet"]
    failed = client.get("/transactions", params={"hash": "B4" * 32, "network": "testnet"})
    assert "Validated" in failed.text and "Failed: tecUNFUNDED_PAYMENT" in failed.text
    assert client.get("/healthz").json()["network"] == SETTINGS.network.name == "testnet"


@pytest.mark.parametrize(
    ("raised", "status", "text"),
    [
        (TransactionNotFound(), 404, "Not found on Mainnet"),
        (TransactionNotValidated(), 409, "not validated yet"),
        (LedgerError(), 502, "lookup failed"),
    ],
)
def test_lookup_errors(store: Store, monkeypatch, raised, status, text) -> None:
    async def fake(endpoints: config.NetworkEndpoints, tx_hash: str) -> dict[str, Any]:
        raise raised

    monkeypatch.setattr(lookup_pages, "lookup_transaction", fake)
    r = make_client(store, "alice").get(
        "/transactions", params={"hash": HASH, "network": "mainnet"}
    )
    assert r.status_code == status and text in r.text
    bad = make_client(store, "alice").get("/transactions", params={"hash": "zz"})
    assert bad.status_code == 422 and "64-character" in bad.text


# --- C. wallet verification ----------------------------------------------------------------


@pytest.fixture
def chain(monkeypatch: pytest.MonkeyPatch):
    payment: dict[str, Any] = {}

    class Endpoint:
        def __init__(self, url: str) -> None:
            pass

        async def request(self, req: Request) -> Response:
            if isinstance(req, Ledger):
                result: dict[str, Any] = {"ledger_index": 800}
            elif isinstance(req, AccountInfo):
                result = {"account_data": {"Balance": "5000000"}}
            else:
                assert isinstance(req, Tx)
                if req.transaction != HASH:
                    return Response(status=ResponseStatus.ERROR, result={"error": "txnNotFound"})
                result = payment
            return Response(status=ResponseStatus.SUCCESS, result=result)

    monkeypatch.setattr(ledger, "AsyncJsonRpcClient", Endpoint)
    monkeypatch.setenv("XRPL_VERIFICATION_RECIPIENT_TESTNET", RECIPIENT)
    return payment


def pay(payment: dict[str, Any], tag: str, validated: bool = True) -> None:
    payment.update(
        hash=HASH,
        validated=validated,
        ledger_index=801,
        tx_json={
            "TransactionType": "Payment",
            "Account": SOURCE,
            "Destination": RECIPIENT,
            "DestinationTag": int(tag),
            "DeliverMax": "1",
        },
        meta={"TransactionResult": "tesSUCCESS", "delivered_amount": "1"},
    )


def start(client: TestClient) -> dict[str, str]:
    import re

    page = client.post(f"/wallets/{SOURCE}/verify/challenge").text
    assert RECIPIENT in page and "1 drop" in page and "Destination tag" in page
    return {
        name: re.search(rf'name="{name}" value="([^"]*)"', page).group(1)
        for name in ("challenge_id", "destination", "destination_tag", "expires_at")
    }


def test_verification_flow_pending_then_confirmed(store: Store, chain) -> None:
    alice = make_client(store, "alice")
    assert "Not verified" in alice.get(f"/wallets/{SOURCE}/verify").text
    fields = start(alice)
    pay(chain, fields["destination_tag"], validated=False)
    pending = alice.post(f"/wallets/{SOURCE}/verify/confirm", data={**fields, "tx_hash": HASH})
    assert pending.status_code == 409 and "Waiting for the ledger" in pending.text
    assert fields["challenge_id"] in pending.text  # the owner can retry with the same challenge
    pay(chain, fields["destination_tag"])
    done = alice.post(f"/wallets/{SOURCE}/verify/confirm", data={**fields, "tx_hash": HASH})
    assert done.status_code == 200 and "You control this wallet" in done.text
    assert "Verified" in alice.get(f"/wallets/{SOURCE}").text
    assert "Not verified" in make_client(store, "bruno").get(f"/wallets/{SOURCE}/verify").text


def test_verification_expired_other_user_and_unavailable(
    store: Store, chain, monkeypatch: pytest.MonkeyPatch
) -> None:
    alice, bruno = make_client(store, "alice"), make_client(store, "bruno")
    fields = start(alice)
    pay(chain, fields["destination_tag"])
    stolen = bruno.post(f"/wallets/{SOURCE}/verify/confirm", data={**fields, "tx_hash": HASH})
    assert stolen.status_code == 404 and "find the wallet" in stolen.text  # not bruno's challenge
    with store.session() as s:
        s.get(WalletChallenge, fields["challenge_id"]).expires_at = utcnow() - timedelta(seconds=1)
    expired = alice.post(f"/wallets/{SOURCE}/verify/confirm", data={**fields, "tx_hash": HASH})
    assert expired.status_code == 410 and "Get new payment details" in expired.text
    monkeypatch.delenv("XRPL_VERIFICATION_RECIPIENT_TESTNET")
    off = alice.post(f"/wallets/{SOURCE}/verify/challenge")
    assert off.status_code == 503 and "available on this deployment" in off.text
