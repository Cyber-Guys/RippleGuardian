"""XRPL reads for proof of control of a watched address."""

from __future__ import annotations

from ixh26.config import NetworkEndpoints
from ixh26.ledger.client import (
    TX_HASH_PATTERN,
    LedgerError,
    TransactionNotFound,
    TransactionNotValidated,
    XrplReader,
    read_transaction,
)
from ixh26.store.models import WalletChallenge

VERIFICATION_DROPS = "1"

__all__ = [
    "TX_HASH_PATTERN",
    "VERIFICATION_DROPS",
    "LedgerError",
    "TransactionNotFound",
    "TransactionNotValidated",
    "payment_matches",
    "recipient_ledger",
]


async def recipient_ledger(network: NetworkEndpoints, address: str) -> int | None:
    """Get a validated starting ledger, if the recipient is a funded classic address."""
    if not XrplReader.valid_address(address):
        return None
    reader = XrplReader(network.json_rpc_url)
    ledger_index = await reader.current_ledger()
    return ledger_index if await reader.xrp_balance(address, ledger_index) > 0 else None


async def payment_matches(
    network: NetworkEndpoints, source: str, challenge: WalletChallenge, tx_hash: str
) -> bool:
    result = await read_transaction(network.json_rpc_url, tx_hash)
    tx = result["tx_json"]
    meta = result["meta"]
    return (
        result["ledger_index"] > challenge.after_ledger
        and meta["TransactionResult"] == "tesSUCCESS"
        and tx.get("TransactionType") == "Payment"
        and tx.get("Account") == source
        and tx.get("Destination") == challenge.destination
        and tx.get("DestinationTag") == challenge.destination_tag
        and "SendMax" not in tx  # The requested payment sends XRP directly.
        and meta.get("delivered_amount") == VERIFICATION_DROPS
    )
