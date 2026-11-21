"""Transaction search by hash on Mainnet or Testnet. The selector only affects this lookup."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ixh26 import config
from ixh26.app.auth import SettingsDep
from ixh26.app.views.common import PageUser, render
from ixh26.flows.transactions import (
    TX_HASH_PATTERN,
    LedgerError,
    TransactionNotFound,
    TransactionNotValidated,
    lookup_transaction,
)

router = APIRouter(include_in_schema=False)
CHOICES = ("mainnet", "testnet")


def summary(found: dict[str, Any]) -> list[tuple[str, str]]:
    """The few fields worth reading first; the full JSON sits behind a disclosure."""
    tx = found["transaction"]
    rows = [("Type", str(tx.get("TransactionType", "")))]
    for key, label in (("Account", "From"), ("Destination", "To")):
        if tx.get(key):
            rows.append((label, str(tx[key])))
    if tx.get("DestinationTag") is not None:
        rows.append(("Destination tag", str(tx["DestinationTag"])))
    return rows


@router.get("/transactions")
async def lookup_page(
    request: Request, user: PageUser, settings: SettingsDep, hash: str = "", network: str = ""
) -> Response:
    chosen = network if network in CHOICES else settings.network.name
    found: dict[str, Any] | None = None
    error = ""
    code = 200
    value = hash.strip()
    if value:
        if not re.fullmatch(TX_HASH_PATTERN, value):
            error, code = "Enter the 64-character transaction hash (letters A-F and digits).", 422
        else:
            try:
                found = await lookup_transaction(config.NETWORKS[chosen], value)
            except TransactionNotFound:
                error, code = f"Not found on {chosen.capitalize()}. Check the network.", 404
            except TransactionNotValidated:
                error, code = "Seen but not validated yet. Try again in a few seconds.", 409
            except LedgerError:
                error, code = "The lookup failed. Try again in a moment.", 502
    return render(
        request,
        "lookup.html",
        user,
        code,
        hash=value,
        chosen=chosen,
        found=found,
        error=error,
        rows=summary(found) if found else [],
        raw=json.dumps(found["metadata"], indent=2, sort_keys=True) if found else "",
        choices=CHOICES,
    )
