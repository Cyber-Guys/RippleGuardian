"""Wallet owners: their wallets, statement, notifications."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from ixh26.app import api
from ixh26.app.auth import StoreDep
from ixh26.app.views.common import PageUser, amount_text, redirect, render, xrp
from ixh26.app.views.models import statement, wallet_state

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request, user: PageUser, store: StoreDep) -> Response:
    if user.is_analyst:
        return redirect("/analyst/findings")
    flagged = store.flagged_targets()
    wallets = [
        {"wallet": w, "status": wallet_state(store, user.id, w.address, flagged)}
        for w in store.wallets(user.id)
    ]
    return render(
        request,
        "user/dashboard.html",
        user,
        wallets=wallets,
        alerts=store.alerts(user.id, limit=8),
        error=request.query_params.get("error"),
    )


@router.post("/wallets")
def wallet_add(
    user: PageUser,
    store: StoreDep,
    address: Annotated[str, Form()],
    label: Annotated[str, Form()] = "",
) -> Response:
    try:
        address = api.require_address(address)
    except HTTPException:
        return redirect("/?error=That+is+not+a+valid+XRPL+address+(it+starts+with+r).")
    if not store.wallet(user.id, address):
        store.add_wallet(user.id, address, label.strip()[:40])
    return redirect(f"/wallets/{address}")


@router.get("/wallets/{address}")
def wallet_page(request: Request, address: str, user: PageUser, store: StoreDep) -> Response:
    wallet = store.wallet(user.id, address)
    if wallet is None:
        raise HTTPException(404, "not one of your wallets")
    flagged = store.flagged_targets()
    transfers = store.transfers_of([address], limit=500)
    return render(
        request,
        "user/wallet.html",
        user,
        wallet=wallet,
        status=wallet_state(store, user.id, address, flagged),
        statement=statement(address, transfers),
        transfers=transfers[::-1][:100],
        amount_text=amount_text,
        flagged=flagged,
        min_outgoing_xrp=xrp(wallet.min_outgoing_drops),
        synced=store.cursor(address) is not None,
        saved=request.query_params.get("saved"),
    )


@router.post("/wallets/{address}/settings")
def wallet_settings(
    address: str,
    user: PageUser,
    store: StoreDep,
    label: Annotated[str, Form()] = "",
    min_outgoing_xrp: Annotated[str, Form()] = "0",
    notify_outgoing: Annotated[bool, Form()] = False,
    notify_security: Annotated[bool, Form()] = False,
    notify_flagged: Annotated[bool, Form()] = False,
) -> Response:
    if store.wallet(user.id, address) is None:
        raise HTTPException(404, "not one of your wallets")
    body = api.WalletSettings(
        label=label.strip()[:40],
        min_outgoing_xrp=min_outgoing_xrp.strip() or "0",
        notify_outgoing=notify_outgoing,
        notify_security=notify_security,
        notify_flagged=notify_flagged,
    )
    store.update_wallet(user.id, address, **api.wallet_settings_fields(body))
    return redirect(f"/wallets/{address}?saved=1")


@router.post("/wallets/{address}/remove")
def wallet_remove(address: str, user: PageUser, store: StoreDep) -> Response:
    store.remove_wallet(user.id, address)
    return redirect("/")


@router.get("/notifications")
def notifications(request: Request, user: PageUser, store: StoreDep) -> Response:
    return render(request, "user/notifications.html", user, alerts=store.alerts(user.id))


@router.post("/notifications/read")
def notifications_read(user: PageUser, store: StoreDep) -> Response:
    store.mark_read(user.id)
    return redirect("/notifications")


@router.get("/ui/unread")
def unread_fragment(request: Request, user: PageUser) -> HTMLResponse:
    return render(request, "partials/unread.html", user)


@router.get("/ui/feed")
def feed_fragment(request: Request, user: PageUser, store: StoreDep, limit: int = 8) -> Response:
    return render(
        request, "partials/feed.html", user, alerts=store.alerts(user.id, limit=min(limit, 100))
    )
