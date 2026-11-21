import pytest
from xrpl.models import Response
from xrpl.models.requests import Request, Tx
from xrpl.models.response import ResponseStatus

from ixh26.ledger.client import (
    LedgerError,
    TransactionNotFound,
    TransactionNotValidated,
    read_transaction,
)

HASH = "A1" * 32


async def test_tx_v2_returns_validated_failure_for_analysis() -> None:
    entry = {
        "hash": HASH,
        "validated": True,
        "ledger_index": 12,
        "tx_json": {"TransactionType": "Payment"},
        "meta": {"TransactionResult": "tecUNFUNDED_PAYMENT"},
    }

    async def send(request: Request) -> Response:
        assert isinstance(request, Tx)
        assert request.api_version == 2 and request.transaction == HASH
        return Response(status=ResponseStatus.SUCCESS, result=entry)

    assert await read_transaction("unused", HASH.lower(), send=send) == entry


@pytest.mark.parametrize(
    ("status", "entry", "error"),
    [
        (ResponseStatus.ERROR, {"error": "txnNotFound"}, TransactionNotFound),
        (ResponseStatus.SUCCESS, {"validated": False}, TransactionNotValidated),
        (
            ResponseStatus.SUCCESS,
            {
                "hash": "B2" * 32,
                "validated": True,
                "ledger_index": 12,
                "tx_json": {},
                "meta": {"TransactionResult": "tesSUCCESS"},
            },
            LedgerError,
        ),
    ],
)
async def test_tx_lookup_errors(status, entry, error) -> None:
    async def send(request: Request) -> Response:
        return Response(status=status, result=entry)

    with pytest.raises(error):
        await read_transaction("unused", HASH, send=send)
