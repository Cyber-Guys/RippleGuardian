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
from ixh26.ledger import client as ledger
from ixh26.store.models import WalletChallenge, utcnow
from ixh26.store.repo import Store

SOURCE = "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY"
RECIPIENT = "rDsbeomae4FXwgQTJp9Rs64Qg9vDiTCdBv"
HASH = "A3" * 32
URL = f"/api/wallets/{SOURCE}/verification"


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch):
    payment: dict[str, Any] = {}
    requested_hashes: list[str] = []

    class Endpoint:
        def __init__(self, url: str) -> None:
            assert url == config.NETWORKS["testnet"].json_rpc_url

        async def request(self, req: Request) -> Response:
            if isinstance(req, Ledger):
                assert req.ledger_index == "validated"
                result = {"ledger_index": 800}
            elif isinstance(req, AccountInfo):
                assert req.account == RECIPIENT
                assert req.ledger_index == 800
                result = {"account_data": {"Balance": "5000000"}}
            else:
                assert isinstance(req, Tx)
                assert req.api_version == 2 and req.transaction is not None
                requested_hashes.append(req.transaction)
                if req.transaction != HASH:
                    return Response(status=ResponseStatus.ERROR, result={"error": "txnNotFound"})
                result = payment
            return Response(status=ResponseStatus.SUCCESS, result=result)

    monkeypatch.setattr(ledger, "AsyncJsonRpcClient", Endpoint)
    monkeypatch.setenv("XRPL_VERIFICATION_RECIPIENT_TESTNET", RECIPIENT)
    store = Store.from_url("sqlite://")
    for username in ("alice", "bruno"):
        user = store.create_user(username, hash_password("testing-123"))
        store.add_wallet(user.id, SOURCE)
    with TestClient(create_app(config.load_settings({}), store)) as c:
        yield c, store, payment, requested_hashes


def headers(client: TestClient, username: str = "alice") -> dict[str, str]:
    response = client.post("/api/login", json={"username": username, "password": "testing-123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def issue(client: TestClient, auth: dict[str, str], payment: dict[str, Any]) -> dict:
    r = client.post(f"{URL}/challenge", headers=auth)
    assert r.status_code == 201, r.text
    challenge = r.json()
    assert challenge["network"] == "testnet"
    assert challenge["source"] == SOURCE and challenge["destination"] == RECIPIENT
    assert challenge["amount_drops"] == "1"
    assert 0 < challenge["destination_tag"] < 2**32
    payment.update(
        {
            "hash": HASH,
            "validated": True,
            "ledger_index": 801,
            "tx_json": {
                "TransactionType": "Payment",
                "Account": SOURCE,
                "Destination": RECIPIENT,
                "DestinationTag": challenge["destination_tag"],
                "DeliverMax": "1",
            },
            "meta": {"TransactionResult": "tesSUCCESS", "delivered_amount": "1"},
        }
    )
    return {"challenge_id": challenge["challenge_id"], "tx_hash": HASH.lower()}


def test_verification_is_persistent_private_and_retryable(ctx) -> None:
    client, _, payment, requested_hashes = ctx
    assert client.get(URL).status_code == 401
    alice = headers(client)
    bruno = headers(client, "bruno")
    assert client.get(URL, headers=alice).json()["verified"] is False
    body = issue(client, alice, payment)
    assert client.post(f"{URL}/confirm", headers=bruno, json=body).status_code == 404
    other_body = issue(client, bruno, {})
    assert client.post(f"{URL}/confirm", headers=bruno, json=other_body).status_code == 422
    assert client.get(URL, headers=bruno).json()["verified"] is False
    r = client.post(f"{URL}/confirm", headers=alice, json=body)
    assert r.status_code == 200, r.text
    assert r.json()["verified"] and r.json()["tx_hash"] == HASH and r.json()["verified_at"]
    assert client.get(URL, headers=alice).json() == r.json()
    assert client.post(f"{URL}/confirm", headers=alice, json=body).json() == r.json()
    wrong_hash = {**body, "tx_hash": "B4" * 32}
    assert client.post(f"{URL}/confirm", headers=alice, json=wrong_hash).status_code == 409
    assert requested_hashes == [HASH, HASH]
    assert client.post(f"{URL}/challenge", headers=alice).status_code == 409

    assert client.delete(f"/api/wallets/{SOURCE}", headers=alice).status_code == 204
    assert client.post("/api/wallets", headers=alice, json={"address": SOURCE}).status_code == 201
    assert client.get(URL, headers=alice).json()["verified"] is False
    assert client.post(f"{URL}/confirm", headers=alice, json=body).status_code == 404


@pytest.mark.parametrize(
    ("section", "field", "value", "status"),
    [
        (None, "validated", False, 409),
        (None, "ledger_index", 800, 422),
        ("tx_json", "Account", RECIPIENT, 422),
        ("tx_json", "Destination", SOURCE, 422),
        ("tx_json", "DestinationTag", 0, 422),
        ("tx_json", "TransactionType", "CheckCash", 422),
        ("tx_json", "SendMax", {"currency": "USD"}, 422),
        ("meta", "TransactionResult", "tecUNFUNDED_PAYMENT", 422),
        ("meta", "delivered_amount", "2", 422),
        ("meta", "delivered_amount", {"currency": "USD", "value": "1"}, 422),
        ("meta", "delivered_amount", None, 422),
    ],
)
def test_verification_rejects_wrong_payments(ctx, section, field, value, status) -> None:
    client, _, payment, _ = ctx
    alice = headers(client)
    body = issue(client, alice, payment)
    target = payment if section is None else payment[section]
    target[field] = value
    assert client.post(f"{URL}/confirm", headers=alice, json=body).status_code == status
    assert client.get(URL, headers=alice).json()["verified"] is False


def test_expired_challenge_skips_rpc_and_bad_recipient_is_rejected(ctx, monkeypatch) -> None:
    client, store, payment, requested_hashes = ctx
    alice = headers(client)
    body = issue(client, alice, payment)
    with store.session() as s:
        challenge = s.get(WalletChallenge, body["challenge_id"])
        assert challenge is not None
        challenge.expires_at = utcnow() - timedelta(seconds=1)
    assert client.post(f"{URL}/confirm", headers=alice, json=body).status_code == 410
    assert requested_hashes == []
    monkeypatch.setenv("XRPL_VERIFICATION_RECIPIENT_TESTNET", f"{RECIPIENT[:-1]}r")
    assert client.post(f"{URL}/challenge", headers=alice).status_code == 503
    monkeypatch.delenv("XRPL_VERIFICATION_RECIPIENT_TESTNET")
    assert client.post(f"{URL}/challenge", headers=alice).status_code == 503
