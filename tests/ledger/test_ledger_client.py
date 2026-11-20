import json
from pathlib import Path

import httpx
import pytest
from xrpl.models import Response
from xrpl.models.requests import Request
from xrpl.models.response import ResponseStatus

from ixh26 import config
from ixh26.ledger.client import LedgerError, XrplReader

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "testnet_xrp_payment.json").read_text())


def _ok(result: dict) -> Response:
    return Response(status=ResponseStatus.SUCCESS, result=result)


async def test_account_activity_follows_markers_and_retries_transport_errors() -> None:
    calls: list[Request] = []
    pages = [
        httpx.ConnectTimeout("boom"),
        _ok({"transactions": [FIXTURE], "marker": {"ledger": 1, "seq": 2}}),
        _ok({"transactions": [FIXTURE]}),
    ]

    async def send(req: Request) -> Response:
        calls.append(req)
        page = pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page

    reader = XrplReader("unused", send=send)
    activity = await reader.account_activity("rA", from_ledger=10)
    assert len(activity) == 2
    assert calls[-1].marker == {"ledger": 1, "seq": 2}
    assert calls[0].ledger_index_min == 10 and calls[0].forward is True


async def test_ledger_errors_are_raised() -> None:
    async def send(req: Request) -> Response:
        return Response(status=ResponseStatus.ERROR, result={"error": "actMalformed"})

    with pytest.raises(LedgerError):
        await XrplReader("unused", send=send).current_ledger()


@pytest.mark.network
async def test_testnet_current_ledger() -> None:
    reader = XrplReader(config.load_settings({}).network.json_rpc_url)
    assert await reader.current_ledger() > 0
