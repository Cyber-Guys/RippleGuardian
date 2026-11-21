"""The ONLY module that reads environment variables (CLAUDE.md §4, §6).

Secrets (wallet seeds, JWT secret) are exposed through accessor functions so that they are
never part of a printable object; ``Settings.__repr__`` therefore never contains a secret.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

DEMO_SEED: Final[int] = 2611  # fixed RNG seed so demo runs are reproducible
TEAM_SOURCE_TAG: Final[int] = 2611_2026  # fallback until the platform assigns one (CHALLENGE Q3)
APP_ID: Final[str] = "ixh26-guardian"


class ConfigError(RuntimeError):
    """Raised when the environment is missing or contains an invalid value."""


@dataclass(frozen=True)
class NetworkEndpoints:
    name: str
    json_rpc_url: str
    websocket_url: str
    explorer_tx_url: str  # format with {hash}
    faucet_host: str | None


NETWORKS: Final[dict[str, NetworkEndpoints]] = {
    "testnet": NetworkEndpoints(
        name="testnet",
        json_rpc_url="https://s.altnet.rippletest.net:51234/",
        websocket_url="wss://s.altnet.rippletest.net:51233/",
        explorer_tx_url="https://testnet.xrpl.org/transactions/{hash}",
        faucet_host=None,  # xrpl-py picks the testnet faucet automatically
    ),
    "devnet": NetworkEndpoints(
        name="devnet",
        json_rpc_url="https://s.devnet.rippletest.net:51234/",
        websocket_url="wss://s.devnet.rippletest.net:51233/",
        explorer_tx_url="https://devnet.xrpl.org/transactions/{hash}",
        faucet_host=None,
    ),
    "mainnet": NetworkEndpoints(
        name="mainnet",
        json_rpc_url="https://xrplcluster.com/",
        websocket_url="wss://xrplcluster.com/",
        explorer_tx_url="https://livenet.xrpl.org/transactions/{hash}",
        faucet_host=None,
    ),
}


@dataclass(frozen=True)
class Settings:
    network: NetworkEndpoints
    source_tag: int
    database_url: str
    redis_url: str
    poll_interval_s: int
    taint_min_ratio: Decimal  # stop propagating below this fraction of the original theft
    taint_min_drops: int  # ...or below this absolute amount (XRP, in drops)
    trace_max_hops: int
    jwt_ttl_minutes: int
    log_level: str


def _get(env: dict[str, str], key: str, default: str) -> str:
    value = env.get(key, default).strip()
    if not value:
        raise ConfigError(f"{key} is set but empty")
    return value


def _int(env: dict[str, str], key: str, default: int, *, minimum: int = 0) -> int:
    raw = _get(env, key, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{key} must be >= {minimum}, got {value}")
    return value


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Build settings from ``env`` (defaults to ``os.environ``)."""
    env = dict(os.environ) if env is None else env
    network_name = _get(env, "XRPL_NETWORK", "testnet").lower()
    if network_name not in NETWORKS:
        raise ConfigError(
            f"XRPL_NETWORK={network_name!r} is not allowed; use one of {sorted(NETWORKS)}"
        )
    database_url = _get(
        env, "DATABASE_URL", "postgresql+psycopg://ixh26:ixh26@localhost:5432/ixh26"
    )
    if network_name == "mainnet":
        mainnet_url = _get(env, "XRPL_MAINNET_DATABASE_URL", "")
        if mainnet_url == database_url:
            raise ConfigError("XRPL_MAINNET_DATABASE_URL must use a separate database")
        database_url = mainnet_url
    ratio_raw = _get(env, "TAINT_MIN_RATIO", "0.01")
    try:
        ratio = Decimal(ratio_raw)
    except ArithmeticError as exc:
        raise ConfigError(f"TAINT_MIN_RATIO must be a decimal, got {ratio_raw!r}") from exc
    if not Decimal(0) < ratio < Decimal(1):
        raise ConfigError(f"TAINT_MIN_RATIO must be in (0, 1), got {ratio}")
    return Settings(
        network=NETWORKS[network_name],
        source_tag=_int(env, "SOURCE_TAG", TEAM_SOURCE_TAG),
        database_url=database_url,
        redis_url=_get(env, "REDIS_URL", "redis://localhost:6379/0"),
        poll_interval_s=_int(env, "POLL_INTERVAL_S", 30, minimum=1),
        taint_min_ratio=ratio,
        taint_min_drops=_int(env, "TAINT_MIN_DROPS", 1_000_000),
        trace_max_hops=_int(env, "TRACE_MAX_HOPS", 6, minimum=1),
        jwt_ttl_minutes=_int(env, "JWT_TTL_MINUTES", 60, minimum=1),
        log_level=_get(env, "LOG_LEVEL", "INFO").upper(),
    )


def jwt_secret(env: dict[str, str] | None = None) -> str:
    """Return the JWT signing secret. Fails loudly if it is missing or too short."""
    env = dict(os.environ) if env is None else env
    secret = env.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise ConfigError("JWT_SECRET must be set to at least 32 characters (see .env.example)")
    return secret


def wallet_seed(name: str, env: dict[str, str] | None = None) -> str:
    """Return the seed stored in ``XRPL_SEED_<NAME>``. Only ``ledger/`` may call this."""
    env = dict(os.environ) if env is None else env
    key = f"XRPL_SEED_{name.upper()}"
    seed = env.get(key, "")
    if not seed:
        raise ConfigError(f"{key} is not set; run scripts/new_wallets.py")
    return seed


def has_wallet_seed(name: str, env: dict[str, str] | None = None) -> bool:
    """Presence check that never exposes the value (CLAUDE.md §6)."""
    env = dict(os.environ) if env is None else env
    return bool(env.get(f"XRPL_SEED_{name.upper()}"))
