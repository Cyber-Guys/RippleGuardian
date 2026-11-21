"""Wallet ownership proof: the user pays one drop with a one-time tag, then pastes the hash."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from pydantic import ValidationError

from ixh26.app.auth import SettingsDep, StoreDep
from ixh26.app.verification import (
    ChallengeOut,
    Confirmation,
    create_challenge,
    verification_status,
    verify_wallet,
)
from ixh26.app.views.common import PageUser, render

router = APIRouter(include_in_schema=False)

# What each status of the confirm call means for the owner, in plain words.
CONFIRM_MESSAGES = {
    404: "We can't find the wallet, the payment details or that payment. Check the hash.",
    409: "This payment or these payment details were already used. Get new details.",
    410: "These payment details expired. Get new ones and pay again.",
    422: "That payment doesn't match the details. Check the amount, recipient and tag.",
    502: "We couldn't read the ledger just now. Try again in a moment.",
    503: "Verification isn't available on this deployment right now.",
}


def view(
    request: Request,
    user: Any,
    address: str,
    store: Any,
    settings: Any,
    *,
    challenge: ChallengeOut | SimpleNamespace | None = None,
    error: str = "",
    code: int = 200,
    pending: bool = False,
    expired: bool = False,
) -> Response:
    status = verification_status(address, user, store, settings)
    return render(
        request,
        "user/verify.html",
        user,
        code,
        address=address,
        status=status,
        challenge=challenge,
        error=error,
        pending=pending,
        expired=expired,
        network=settings.network.name,
    )


@router.get("/wallets/{address}/verify")
def verify_page(
    request: Request, address: str, user: PageUser, store: StoreDep, settings: SettingsDep
) -> Response:
    try:
        return view(request, user, address, store, settings)
    except HTTPException as exc:
        raise HTTPException(404, "not one of your wallets") from exc


@router.post("/wallets/{address}/verify/challenge")
async def verify_challenge(
    request: Request, address: str, user: PageUser, store: StoreDep, settings: SettingsDep
) -> Response:
    try:
        challenge = await create_challenge(address, user, store, settings)
    except HTTPException as exc:
        message = {
            409: "This wallet is already verified.",
            422: "The wallet and the verification recipient can't be the same.",
            502: "We couldn't reach the ledger. Try again in a moment.",
            503: "Verification isn't available on this deployment right now.",
        }.get(exc.status_code, "We couldn't start the verification.")
        return view(request, user, address, store, settings, error=message, code=exc.status_code)
    return view(request, user, address, store, settings, challenge=challenge)


@router.post("/wallets/{address}/verify/confirm")
async def verify_confirm(
    request: Request,
    address: str,
    user: PageUser,
    store: StoreDep,
    settings: SettingsDep,
    challenge_id: Annotated[str, Form()],
    tx_hash: Annotated[str, Form()],
    destination: Annotated[str, Form()] = "",
    destination_tag: Annotated[str, Form()] = "",
    expires_at: Annotated[str, Form()] = "",
) -> Response:
    # The details are only echoed back so the owner can retry; the server checks its own copy.
    echo = SimpleNamespace(
        challenge_id=challenge_id.strip(),
        destination=destination,
        destination_tag=destination_tag,
        expires_at=expires_at,
        source=address,
        amount_drops="1",
        network=settings.network.name,
    )
    try:
        body = Confirmation(challenge_id=challenge_id.strip(), tx_hash=tx_hash.strip())
        await verify_wallet(address, body, user, store, settings)
    except ValidationError:
        return view(
            request,
            user,
            address,
            store,
            settings,
            code=422,
            challenge=echo,
            error="Paste the 64-character hash of your payment.",
        )
    except HTTPException as exc:
        expired = exc.status_code == 410
        pending = exc.status_code == 409 and "not yet validated" in str(exc.detail)
        return view(
            request,
            user,
            address,
            store,
            settings,
            code=exc.status_code,
            challenge=None if expired else echo,
            error=""
            if pending
            else CONFIRM_MESSAGES.get(exc.status_code, "We couldn't confirm the payment."),
            pending=pending,
            expired=expired,
        )
    return view(request, user, address, store, settings)
