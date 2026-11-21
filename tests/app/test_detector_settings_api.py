from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ixh26 import config
from ixh26.app.auth import hash_password
from ixh26.app.main import create_app
from ixh26.core.detection import DetectionSettings
from ixh26.flows import smoke
from ixh26.flows.detection_settings import DetectorThresholds, effective_detection_settings
from ixh26.flows.monitor import Monitor
from ixh26.store.repo import Store

URL = "/api/detection-settings"


@pytest.fixture
def clients(tmp_path: Path) -> Iterator[tuple[TestClient, Store]]:
    url = f"sqlite:///{tmp_path.as_posix()}/detection.db"
    api_store = Store.from_url(url)
    worker_store = Store.from_url(url)
    password_hash = hash_password("test-password")
    api_store.create_user("analyst", password_hash, role="analyst")
    api_store.create_user("wallet-owner", password_hash)
    with TestClient(create_app(config.load_settings({}), api_store)) as client:
        yield client, worker_store


def _login(client: TestClient, username: str = "analyst") -> dict[str, str]:
    response = client.post("/api/login", json={"username": username, "password": "test-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_settings_are_analyst_only(clients: tuple[TestClient, Store]) -> None:
    client, _ = clients
    defaults = DetectorThresholds.defaults().model_dump(mode="json")
    assert client.get(URL).status_code == 401
    assert client.put(URL, json={"version": 0, "thresholds": defaults}).status_code == 401

    headers = _login(client, "wallet-owner")
    assert client.get(URL, headers=headers).status_code == 403
    assert (
        client.put(URL, headers=headers, json={"version": 0, "thresholds": defaults}).status_code
        == 403
    )


def test_update_all_detectors_round_trips_exactly_and_rejects_stale_edits(
    clients: tuple[TestClient, Store],
) -> None:
    client, store = clients
    headers = _login(client)
    response = client.get(URL, headers=headers)
    assert response.status_code == 200
    view = response.json()
    assert view["version"] == 0 and view["updated_at"] is None
    assert view["thresholds"] == view["defaults"]
    assert view["defaults"]["funnel_window_seconds"] == 1800
    assert view["defaults"]["wash_min_pair_fills"] == 2
    assert view["defaults"]["liquidity_min_pool_drops"] == "10000000"
    assert view["defaults"]["takeover_min_outflow"] == "0.7"
    assert effective_detection_settings(store) == DetectionSettings()

    customized = {
        "funnel_window_seconds": 2700,
        "funnel_min_senders": 4,
        "funnel_min_fraction": "0.82",
        "wash_window_seconds": 1200,
        "wash_min_pair_fills": 3,
        "wash_min_fills": 8,
        "wash_max_wallets": 10,
        "wash_max_net_ratio": "0.0000001",
        "wash_min_market_share": "0.65",
        "liquidity_window_seconds": 5400,
        "liquidity_min_buyers": 4,
        "liquidity_min_pool_drops": "10000000000000001",
        "liquidity_min_drop": "0.65",
        "liquidity_sale_size": "2300.25",
        "takeover_window_seconds": 1200,
        "takeover_min_outflow": "0.75",
    }
    response = client.put(URL, headers=headers, json={"version": 0, "thresholds": customized})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["version"] == 1 and saved["updated_at"].endswith("Z")
    assert saved["thresholds"] == customized and saved["defaults"] == view["defaults"]
    assert client.get(URL, headers=headers).json() == saved
    assert (
        effective_detection_settings(store)
        == DetectorThresholds.model_validate(customized).to_engine()
    )
    assert (
        client.put(URL, headers=headers, json={"version": 0, "thresholds": customized}).status_code
        == 409
    )
    assert client.get(URL, headers=headers).json() == saved

    response = client.put(URL, headers=headers, json={"version": 1, "thresholds": view["defaults"]})
    assert response.status_code == 200 and response.json()["version"] == 2
    assert effective_detection_settings(store) == DetectionSettings()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("funnel_window_seconds", 0),
        ("takeover_window_seconds", 2**31),
        ("funnel_min_senders", True),
        ("wash_min_pair_fills", 1),
        ("wash_min_fills", "6"),
        ("wash_max_net_ratio", "1.01"),
        ("funnel_min_fraction", "0"),
        ("wash_min_market_share", 0.5),
        ("liquidity_min_pool_drops", "0"),
        ("liquidity_min_pool_drops", "1.5"),
        ("liquidity_sale_size", "NaN"),
        ("takeover_min_outflow", None),
        ("takevoer_min_outflow", "0.5"),
    ],
)
def test_settings_validation_identifies_field(name: str, value: object) -> None:
    from pydantic import ValidationError

    thresholds = DetectorThresholds.defaults().model_dump(mode="json")
    with pytest.raises(ValidationError) as error:
        DetectorThresholds.model_validate({**thresholds, name: value})
    assert error.value.errors()[0]["loc"] == (name,)


def test_rejected_api_update_leaves_active_revision_untouched(
    clients: tuple[TestClient, Store],
) -> None:
    client, store = clients
    headers = _login(client)
    defaults = DetectorThresholds.defaults().model_dump(mode="json")
    response = client.put(
        URL,
        headers=headers,
        json={"version": 0, "thresholds": {**defaults, "takeover_min_outflow": "2"}},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "thresholds", "takeover_min_outflow"]
    assert client.get(URL, headers=headers).json()["version"] == 0
    assert effective_detection_settings(store) == DetectionSettings()


def test_running_monitor_reloads_settings_after_api_update(
    clients: tuple[TestClient, Store],
) -> None:
    client, store = clients
    headers = _login(client)
    monitor = Monitor(store)
    rekey, drain, *_ = smoke.scenario()
    monitor.process(rekey)

    defaults = DetectorThresholds.defaults().model_dump(mode="json")
    strict = {**defaults, "takeover_min_outflow": "0.99"}
    response = client.put(URL, headers=headers, json={"version": 0, "thresholds": strict})
    assert response.status_code == 200
    monitor.process(drain)
    assert store.findings() == []

    response = client.put(URL, headers=headers, json={"version": 1, "thresholds": defaults})
    assert response.status_code == 200
    assert store.findings() == []
    (finding,) = monitor.run_detectors([smoke.VICTIM])
    assert finding.kind == "possible_takeover"
    assert monitor.run_detectors([smoke.VICTIM]) == []
