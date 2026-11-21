import pytest
from fastapi.testclient import TestClient
from xrpl.models import Response
from xrpl.models.requests import Tx
from xrpl.models.response import ResponseStatus
from xrpl.models.transactions import Payment

from ixh26 import config
from ixh26.app.auth import hash_password
from ixh26.app.main import create_app
from ixh26.ledger import client as ledger
from ixh26.store.repo import Store

HASH = "A2" * 32
SOURCE = "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY"
DESTINATION = "rDsbeomae4FXwgQTJp9Rs64Qg9vDiTCdBv"


def test_hash_lookup_chooses_network_without_switching_the_watched_database(monkeypatch) -> None:
    urls: list[str] = []

    class Endpoint:
        def __init__(self, url: str) -> None:
            self.url = url

        async def request(self, req: Tx) -> Response:
            urls.append(self.url)
            assert req.transaction == HASH
            if self.url == config.NETWORKS["testnet"].json_rpc_url:
                return Response(status=ResponseStatus.ERROR, result={"error": "txnNotFound"})
            return Response(
                status=ResponseStatus.SUCCESS,
                result={
                    "hash": HASH,
                    "validated": True,
                    "ledger_index": 23,
                    "tx_json": {"TransactionType": "Payment"},
                    "meta": {"TransactionResult": "tesSUCCESS", "delivered_amount": "1"},
                },
            )

    monkeypatch.setattr(ledger, "AsyncJsonRpcClient", Endpoint)
    store = Store.from_url("sqlite://")
    user = store.create_user("analyst", hash_password("testing-123"))
    store.add_wallet(user.id, SOURCE)
    path = f"/api/transactions/{HASH.lower()}"
    with TestClient(create_app(config.load_settings({}), store)) as client:
        assert client.get(path).status_code == 401
        login = client.post("/api/login", json={"username": "analyst", "password": "testing-123"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/api/transactions/oops", headers=headers).status_code == 422
        assert client.get(path, params={"network": "invalid"}, headers=headers).status_code == 422
        assert client.get(path, headers=headers).status_code == 404
        response = client.get(path, params={"network": "mainnet"}, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["metadata"]["delivered_amount"] == "1"
        assert response.json()["explorer_url"] == f"https://livenet.xrpl.org/transactions/{HASH}"
        assert response.json()["network"] == "mainnet"
        assert client.get("/healthz").json()["network"] == "testnet"
        assert client.get("/api/wallets", headers=headers).json()[0]["address"] == SOURCE
    assert urls == [
        config.NETWORKS["testnet"].json_rpc_url,
        config.NETWORKS["mainnet"].json_rpc_url,
    ]


def test_switching_deployments_rejects_sessions_from_the_other_network() -> None:
    db = Store.from_url("sqlite://")
    mainnet_db = Store.for_network("sqlite://", network="mainnet")
    testnet_user = db.create_user("ada-test", hash_password("testing-123"))
    mainnet_user = mainnet_db.create_user("ada-main", hash_password("testing-123"), role="analyst")
    assert testnet_user.id == mainnet_user.id
    testnet = config.load_settings({})
    mainnet = config.load_settings(
        {"XRPL_NETWORK": "mainnet", "XRPL_MAINNET_DATABASE_URL": "sqlite:///mainnet.db"}
    )
    with (
        TestClient(create_app(testnet, db)) as test_client,
        TestClient(create_app(mainnet, mainnet_db)) as main_client,
    ):
        login = test_client.post(
            "/api/login", json={"username": "ada-test", "password": "testing-123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert test_client.get("/api/me", headers=headers).status_code == 200
        assert main_client.get("/healthz").json()["network"] == "mainnet"
        assert main_client.get("/api/me", headers=headers).status_code == 401


async def test_submit_refuses_mainnet_before_opening_client(monkeypatch) -> None:
    def forbidden_client(url: str) -> None:
        pytest.fail("mainnet submission opened an XRPL client")

    monkeypatch.setattr(ledger, "AsyncJsonRpcClient", forbidden_client)
    settings = config.load_settings(
        {"XRPL_NETWORK": "mainnet", "XRPL_MAINNET_DATABASE_URL": "sqlite:///mainnet.db"}
    )
    payment = Payment(account=SOURCE, destination=DESTINATION, amount="1")
    with pytest.raises(ledger.LedgerError, match="test networks"):
        await ledger.submit(settings, payment, ledger.Wallet.create(), "offline unit test")
