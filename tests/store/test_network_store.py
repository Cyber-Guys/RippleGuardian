from pathlib import Path

import pytest

from ixh26.store.repo import NetworkMismatch, Store


def test_legacy_testnet_database_is_preserved_and_mainnet_needs_own_db(tmp_path: Path) -> None:
    test_url = f"sqlite:///{tmp_path / 'testnet.db'}"
    main_url = f"sqlite:///{tmp_path / 'mainnet.db'}"
    legacy = Store.from_url(test_url)
    analyst = legacy.create_user("ana", "fake-hash", "analyst")
    legacy.add_wallet(analyst.id, "rTestWallet")
    legacy.set_cursor("rTestWallet", 42)

    with pytest.raises(NetworkMismatch, match="fresh"):
        Store.for_network(test_url, network="mainnet")
    test = Store.for_network(test_url, network="testnet")
    assert test.watched_addresses() == ["rTestWallet"]
    assert test.cursor("rTestWallet") == 42

    main = Store.for_network(main_url, network="mainnet")
    assert main.watched_addresses() == []
    assert main.cursor("rTestWallet") is None
    assert Store.for_network(main_url, network="mainnet").watched_addresses() == []
    with pytest.raises(NetworkMismatch, match="bound to mainnet"):
        Store.for_network(main_url, network="testnet")
    with pytest.raises(NetworkMismatch, match="bound to testnet"):
        Store.for_network(test_url, network="mainnet")
