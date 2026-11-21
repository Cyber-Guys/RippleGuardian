"""Transaction lookup used by API flows."""

from typing import Any

from ixh26.config import NetworkEndpoints
from ixh26.ledger.client import (
    TX_HASH_PATTERN,
    LedgerError,
    TransactionNotFound,
    TransactionNotValidated,
    read_transaction,
)

__all__ = [
    "TX_HASH_PATTERN",
    "LedgerError",
    "TransactionNotFound",
    "TransactionNotValidated",
    "lookup_transaction",
]


async def lookup_transaction(endpoints: NetworkEndpoints, tx_hash: str) -> dict[str, Any]:
    tx = await read_transaction(endpoints.json_rpc_url, tx_hash)
    canonical_hash = tx["hash"].upper()
    return {
        "network": endpoints.name,
        "hash": canonical_hash,
        "ledger_index": tx["ledger_index"],
        "validated": tx["validated"],
        "result": tx["meta"]["TransactionResult"],
        "transaction": tx["tx_json"],
        "metadata": tx["meta"],
        "explorer_url": endpoints.explorer_tx_url.format(hash=canonical_hash),
    }
