"""Testnet operations used by the demo scripts. Every write goes through ``client.submit``."""

from __future__ import annotations

import logging
from decimal import Decimal

from xrpl.asyncio.clients import AsyncJsonRpcClient
from xrpl.asyncio.wallet import generate_faucet_wallet
from xrpl.models.requests import AccountInfo, ServerInfo
from xrpl.models.transactions import Payment, SetRegularKey
from xrpl.wallet import Wallet

from ixh26 import config
from ixh26.contracts import TxResult
from ixh26.ledger.client import XrplReader, load_wallet, request_with_retry, submit

log = logging.getLogger(__name__)


def _require_test_network(settings: config.Settings) -> None:
    if settings.network.name not in ("testnet", "devnet"):
        raise RuntimeError("demo operations run on test networks only")


async def base_reserve_drops(settings: config.Settings) -> Decimal:
    client = AsyncJsonRpcClient(settings.network.json_rpc_url)
    info = await request_with_retry(client.request, ServerInfo())
    xrp = Decimal(str(info["info"]["validated_ledger"]["reserve_base_xrp"]))
    return xrp * 1_000_000


async def new_faucet_seed(settings: config.Settings) -> tuple[str, str]:
    """(address, seed) of a new funded Testnet wallet. Callers write the seed to .env only."""
    _require_test_network(settings)
    client = AsyncJsonRpcClient(settings.network.json_rpc_url)
    wallet = await generate_faucet_wallet(client, faucet_host=settings.network.faucet_host)
    return wallet.classic_address, wallet.seed or ""


async def ensure_funded(settings: config.Settings, name: str, min_drops: Decimal) -> Wallet:
    """Wallet ``XRPL_SEED_<NAME>``, topped up from the faucet below ``min_drops`` (idempotent)."""
    _require_test_network(settings)
    wallet = load_wallet(name)
    reader = XrplReader(settings.network.json_rpc_url)
    if await reader.xrp_balance(wallet.classic_address) < min_drops:
        client = AsyncJsonRpcClient(settings.network.json_rpc_url)
        await generate_faucet_wallet(client, wallet, faucet_host=settings.network.faucet_host)
        log.info("topped up %s from the faucet", name)
    return wallet


def ephemeral_wallet() -> Wallet:
    """A throwaway key pair for one demo run. Its seed is never stored or printed."""
    return Wallet.create()


async def regular_key_of(settings: config.Settings, address: str) -> str | None:
    client = AsyncJsonRpcClient(settings.network.json_rpc_url)
    result = await request_with_retry(client.request, AccountInfo(account=address))
    return result["account_data"].get("RegularKey")


async def set_regular_key(
    settings: config.Settings, owner: Wallet, regular_key: str | None, purpose: str
) -> TxResult:
    tx = SetRegularKey(account=owner.classic_address, regular_key=regular_key)
    return await submit(settings, tx, owner, purpose)


async def pay_xrp(
    settings: config.Settings,
    signer: Wallet,
    source: str,
    destination: str,
    drops: Decimal,
    purpose: str,
    destination_tag: int | None = None,
) -> TxResult:
    """XRP payment from ``source`` signed by ``signer`` (its master or regular key)."""
    if drops <= 0 or drops != drops.to_integral_value():
        raise ValueError(f"payment amount must be positive integer drops, got {drops}")
    tx = Payment(
        account=source,
        destination=destination,
        amount=str(int(drops)),
        destination_tag=destination_tag,
    )
    return await submit(settings, tx, signer, purpose)
