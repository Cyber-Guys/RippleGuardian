import pytest
from fastapi.testclient import TestClient

from ixh26 import config
from ixh26.app.auth import hash_password
from ixh26.app.main import create_app
from ixh26.store.repo import Store

ADDR = "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY"


@pytest.fixture
def ctx() -> tuple[TestClient, Store]:
    store = Store.from_url("sqlite://")
    store.create_user("ana", hash_password("analyst-pass"), role="analyst")
    client = TestClient(create_app(config.load_settings({}), store))
    return client, store


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_user_flow_and_role_enforcement(ctx: tuple[TestClient, Store]) -> None:
    client, _ = ctx
    assert (
        client.post("/api/register", json={"username": "user1", "password": "p"}).status_code == 422
    )
    assert (
        client.post(
            "/api/register", json={"username": "user1", "password": "password1"}
        ).status_code
        == 201
    )
    user = login(client, "user1", "password1")
    assert client.post("/api/wallets", json={"address": "nope"}, headers=user).status_code == 422
    assert client.post("/api/wallets", json={"address": ADDR}, headers=user).status_code == 201
    assert [w["address"] for w in client.get("/api/wallets", headers=user).json()] == [ADDR]
    r = client.patch(f"/api/wallets/{ADDR}", json={"min_outgoing_xrp": "2.5"}, headers=user)
    assert r.status_code == 200
    assert client.get("/api/wallets", headers=user).json()[0]["min_outgoing_drops"] == "2500000"
    assert client.get("/api/findings", headers=user).status_code == 403
    assert (
        client.post(
            "/api/flags", json={"target": ADDR, "reason": "x" * 5}, headers=user
        ).status_code
        == 403
    )


def test_analyst_flags_are_visible_to_users(ctx: tuple[TestClient, Store]) -> None:
    client, _ = ctx
    ana = login(client, "ana", "analyst-pass")
    body = {"target": ADDR, "category": "theft", "reason": "drained victim wallet"}
    assert client.post("/api/flags", json=body, headers=ana).status_code == 201
    client.post("/api/register", json={"username": "user2", "password": "password2"})
    user = login(client, "user2", "password2")
    flags = client.get("/api/flags", headers=user).json()
    assert flags[0]["target"] == ADDR and flags[0]["analyst"] == "ana"
    r = client.post(
        "/api/traces", json={"origin": ADDR, "stolen_xrp": "50", "start_ledger": 10}, headers=ana
    )
    assert r.status_code == 202
    assert client.get(f"/api/traces/{r.json()['id']}", headers=ana).json()["status"] == "pending"
