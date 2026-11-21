from decimal import Decimal

import pytest

from ixh26 import config


def test_defaults_are_testnet_and_one_percent_threshold() -> None:
    s = config.load_settings({})
    assert s.network.name == "testnet"
    assert s.taint_min_ratio == Decimal("0.01")
    assert s.source_tag == config.TEAM_SOURCE_TAG


@pytest.mark.parametrize("net", ["livenet", "foo"])
def test_unknown_networks_are_refused(net: str) -> None:
    with pytest.raises(config.ConfigError, match="not allowed"):
        config.load_settings({"XRPL_NETWORK": net})


def test_mainnet_requires_its_own_database_url() -> None:
    with pytest.raises(config.ConfigError, match="XRPL_MAINNET_DATABASE_URL"):
        config.load_settings({"XRPL_NETWORK": "mainnet"})
    with pytest.raises(config.ConfigError, match="separate database"):
        config.load_settings(
            {
                "XRPL_NETWORK": "mainnet",
                "DATABASE_URL": "sqlite:///testnet.db",
                "XRPL_MAINNET_DATABASE_URL": "sqlite:///testnet.db",
            }
        )
    settings = config.load_settings(
        {
            "XRPL_NETWORK": "MAINNET",
            "DATABASE_URL": "sqlite:///testnet.db",
            "XRPL_MAINNET_DATABASE_URL": "sqlite:///mainnet.db",
        }
    )
    assert settings.network == config.NETWORKS["mainnet"]
    assert settings.database_url == "sqlite:///mainnet.db"


@pytest.mark.parametrize("ratio", ["0", "1", "-0.1", "abc"])
def test_invalid_taint_ratio_fails_loudly(ratio: str) -> None:
    with pytest.raises(config.ConfigError):
        config.load_settings({"TAINT_MIN_RATIO": ratio})


def test_bad_integer_fails_loudly() -> None:
    with pytest.raises(config.ConfigError, match="TRACE_MAX_HOPS"):
        config.load_settings({"TRACE_MAX_HOPS": "lots"})


def test_jwt_secret_required_and_not_in_settings_repr() -> None:
    with pytest.raises(config.ConfigError):
        config.jwt_secret({})
    secret = "x" * 40
    assert config.jwt_secret({"JWT_SECRET": secret}) == secret
    assert secret not in repr(config.load_settings({"JWT_SECRET": secret}))


def test_wallet_seed_presence_check_does_not_need_value() -> None:
    env = {"XRPL_SEED_VICTIM": "placeholder"}
    assert config.has_wallet_seed("victim", env)
    assert not config.has_wallet_seed("attacker", env)
    with pytest.raises(config.ConfigError, match="XRPL_SEED_ATTACKER"):
        config.wallet_seed("attacker", env)
