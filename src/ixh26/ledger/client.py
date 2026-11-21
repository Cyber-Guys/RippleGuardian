"""The single XRPL client module (CLAUDE.md §5): read side, live stream and submit helper."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from xrpl.asyncio.clients import AsyncJsonRpcClient, AsyncWebsocketClient
from xrpl.asyncio.clients.exceptions import XRPLRequestFailureException
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.asyncio.wallet import generate_faucet_wallet
from xrpl.core.addresscodec import is_valid_classic_address
from xrpl.models import Memo, Response
from xrpl.models.requests import AccountInfo, AccountTx, Ledger, Request, Subscribe, Tx
from xrpl.models.transactions import Transaction
from xrpl.utils import str_to_hex
from xrpl.wallet import Wallet

from ixh26 import config
from ixh26.contracts import AccountActivity, TxResult
from ixh26.ledger.normalize import normalize

log = logging.getLogger(__name__)

TX_LOG = Path("artifacts/tx_log.jsonl")
Requester = Callable[[Request], Awaitable[Response]]
TX_HASH_PATTERN = r"^[0-9A-Fa-f]{64}$"


class LedgerError(RuntimeError):
    """The ledger answered with an error, or a submission did not reach tesSUCCESS."""


class TransactionNotFound(LedgerError):
    """The selected server could not find the transaction."""


class TransactionNotValidated(LedgerError):
    """The transaction is present but is not final."""


async def request_with_retry(send: Requester, req: Request, *, attempts: int = 4) -> dict[str, Any]:
    """Send ``req``; retry transport errors with exponential backoff; raise on ledger errors."""
    for attempt in range(attempts):
        try:
            response = await send(req)
        except (httpx.HTTPError, OSError, XRPLRequestFailureException) as exc:
            if attempt == attempts - 1:
                raise LedgerError(f"{req.method} failed after {attempts} attempts") from exc
            delay = 0.5 * 2**attempt
            log.warning(
                "%s transport error (%s), retry in %.1fs", req.method, type(exc).__name__, delay
            )
            await asyncio.sleep(delay)
            continue
        if not response.is_successful():
            raise LedgerError(f"{req.method} error: {response.result}")
        return response.result
    raise AssertionError("unreachable")


async def read_transaction(
    url: str, tx_hash: str, *, send: Requester | None = None
) -> dict[str, Any]:
    """Read a final transaction by hash, including failed transactions and their metadata."""
    if not re.fullmatch(TX_HASH_PATTERN, tx_hash):
        raise ValueError("expected a 64-character hexadecimal transaction hash")
    tx_hash = tx_hash.upper()
    request = send or AsyncJsonRpcClient(url).request

    async def send_tx(req: Request) -> Response:
        response = await request(req)
        if not response.is_successful() and response.result.get("error") == "txnNotFound":
            raise TransactionNotFound(tx_hash)
        return response

    result = await request_with_retry(send_tx, Tx(transaction=tx_hash, api_version=2))
    if result.get("validated") is not True:
        raise TransactionNotValidated(tx_hash)
    tx = result.get("tx_json")
    meta = result.get("meta")
    returned_hash = result.get("hash")
    ledger_index = result.get("ledger_index")
    if (
        not isinstance(tx, dict)
        or not isinstance(meta, dict)
        or not isinstance(meta.get("TransactionResult"), str)
        or not isinstance(returned_hash, str)
        or returned_hash.upper() != tx_hash
        or type(ledger_index) is not int
        or ledger_index <= 0
    ):
        raise LedgerError("invalid response to tx lookup")
    return result


class XrplReader:
    """``LedgerReader`` over JSON-RPC. Inject ``send`` in tests to stay offline."""

    def __init__(self, url: str, *, send: Requester | None = None, page_limit: int = 200) -> None:
        self._send = send or AsyncJsonRpcClient(url).request
        self._page_limit = page_limit

    async def _call(self, req: Request) -> dict[str, Any]:
        return await request_with_retry(self._send, req)

    async def account_activity(
        self, account: str, *, from_ledger: int, to_ledger: int | None = None
    ) -> Sequence[AccountActivity]:
        """Every validated tx of ``account`` in [from_ledger, to_ledger], oldest first."""
        out: list[AccountActivity] = []
        marker: Any = None
        while True:
            result = await self._call(
                AccountTx(
                    account=account,
                    ledger_index_min=from_ledger,
                    ledger_index_max=to_ledger if to_ledger is not None else -1,
                    forward=True,
                    limit=self._page_limit,
                    marker=marker,
                )
            )
            out.extend(normalize(entry) for entry in result.get("transactions", ()))
            marker = result.get("marker")
            if marker is None:
                return out

    async def current_ledger(self) -> int:
        result = await self._call(Ledger(ledger_index="validated"))
        return int(result["ledger_index"])

    @staticmethod
    def valid_address(address: str) -> bool:
        return is_valid_classic_address(address)

    async def xrp_balance(self, account: str, ledger_index: int | str = "validated") -> Decimal:
        """Balance in drops at ``ledger_index``; 0 if the account did not exist then."""
        try:
            result = await self._call(AccountInfo(account=account, ledger_index=ledger_index))
        except LedgerError as exc:
            if "actNotFound" in str(exc):
                return Decimal(0)
            raise
        return Decimal(result["account_data"]["Balance"])


class XrplStream:
    """``LedgerStream``: validated transactions for a set of accounts over WebSocket."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def watch(self, accounts: Sequence[str]) -> AsyncIterator[AccountActivity]:
        async with AsyncWebsocketClient(self._url) as client:
            await client.send(Subscribe(accounts=list(accounts)))
            async for message in client:
                if message.get("type") == "transaction" and message.get("validated"):
                    yield normalize(message)


# --- write path -------------------------------------------------------------------------------


def load_wallet(name: str) -> Wallet:
    """Wallet from ``XRPL_SEED_<NAME>``; the seed never leaves this process."""
    return Wallet.from_seed(config.wallet_seed(name))


async def faucet_wallet(settings: config.Settings) -> Wallet:
    if settings.network.name not in ("testnet", "devnet"):
        raise LedgerError("faucet is only available on test networks")
    client = AsyncJsonRpcClient(settings.network.json_rpc_url)
    return await generate_faucet_wallet(client, faucet_host=settings.network.faucet_host)


async def submit(
    settings: config.Settings,
    tx: Transaction,
    wallet: Wallet,
    purpose: str,
    *,
    tx_log: Path = TX_LOG,
) -> TxResult:
    """The ONLY submission path: SourceTag + memo, submit_and_wait, require tesSUCCESS, log."""
    if settings.network.name not in ("testnet", "devnet"):
        raise LedgerError("transaction submission is only available on test networks")
    memo = Memo(
        memo_type=str_to_hex("ixh26/purpose"),
        memo_data=str_to_hex(f"{config.APP_ID}:{purpose}"[:120]),
    )
    tx = replace(tx, source_tag=settings.source_tag, memos=[*(tx.memos or []), memo])
    client = AsyncJsonRpcClient(settings.network.json_rpc_url)
    response = await submit_and_wait(tx, client, wallet)
    result = response.result
    meta = result.get("meta", {})
    if not result.get("validated") or meta.get("TransactionResult") != "tesSUCCESS":
        raise LedgerError(f"{purpose}: {meta.get('TransactionResult', 'not validated')}")
    tx_hash = result["hash"]
    record = TxResult(
        tx_hash=tx_hash,
        tx_type=tx.transaction_type.value,
        network=settings.network.name,
        ledger_index=int(result["ledger_index"]),
        purpose=purpose,
        explorer_url=settings.network.explorer_tx_url.format(hash=tx_hash),
        submitted_at=datetime.now(UTC),
        meta=meta,
    )
    tx_log.parent.mkdir(parents=True, exist_ok=True)
    with tx_log.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "time": record.submitted_at.isoformat(),
                    "network": record.network,
                    "tx_type": record.tx_type,
                    "hash": record.tx_hash,
                    "purpose": purpose,
                    "explorer_url": record.explorer_url,
                }
            )
            + "\n"
        )
    log.info("%s %s %s", record.tx_type, purpose, record.explorer_url)
    return record
