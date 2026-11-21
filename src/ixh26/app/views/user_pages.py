"""Wallet owners: their wallets, statement, notifications."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from ixh26 import config
from ixh26.app import api
from ixh26.app.auth import CurrentUser, SettingsDep, StoreDep
from ixh26.app.charts import line_chart
from ixh26.app.views.common import PageUser, amount_text, redirect, render, xrp
from ixh26.app.views.models import (
    balance_points,
    last_activity,
    overall_state,
    statement,
    user_kpis,
    wallet_state,
)
from ixh26.contracts import XRP
from ixh26.flows.report import Incident, build_incident, incident_pdf
from ixh26.store.repo import Store
from ixh26.store.verification import get_proof

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request, user: PageUser, store: StoreDep) -> Response:
    if user.is_analyst:
        return redirect("/analyst")
    flagged = store.flagged_targets()
    wallets = [
        {
            "wallet": w,
            "status": wallet_state(store, user.id, w.address, flagged),
            "last": last_activity(store, w.address),
        }
        for w in store.wallets(user.id)
    ]
    return render(
        request,
        "user/dashboard.html",
        user,
        wallets=wallets,
        kpis=user_kpis(store, user.id, [w["wallet"] for w in wallets]),
        overall=overall_state(
            [(w["wallet"].label or "One of your wallets", w["status"]) for w in wallets]
        ),
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
def wallet_page(
    request: Request, address: str, user: PageUser, store: StoreDep, settings: SettingsDep
) -> Response:
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
        balance_chart=line_chart(balance_points(address, transfers), unit="XRP"),
        transfers=transfers[::-1][:100],
        amount_text=amount_text,
        flagged=flagged,
        min_outgoing_xrp=xrp(wallet.min_outgoing_drops),
        synced=store.cursor(address) is not None,
        verified=get_proof(store, wallet, settings.network.name) is not None,
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


def _incident(store: Store, user: CurrentUser, address: str, settings: config.Settings) -> Incident:
    try:
        return build_incident(store, user.id, address, settings)
    except LookupError:
        raise HTTPException(404, "not one of your wallets") from None


@router.get("/wallets/{address}/recover")
def recover_page(
    request: Request, address: str, user: PageUser, store: StoreDep, settings: SettingsDep
) -> Response:
    """The step-by-step screen for an owner whose wallet was taken over."""
    incident = _incident(store, user, address, settings)
    return render(request, "user/recover.html", user, i=incident, stolen=xrp(incident.stolen_drops))


@router.get("/wallets/{address}/report.pdf")
def report_pdf(address: str, user: PageUser, store: StoreDep, settings: SettingsDep) -> Response:
    incident = _incident(store, user, address, settings)
    return Response(
        incident_pdf(incident, settings),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{incident.reference}.pdf"'},
    )


@router.post("/wallets/{address}/trace")
def request_trace(address: str, user: PageUser, store: StoreDep, settings: SettingsDep) -> Response:
    """Owners can queue one trace of their own theft; the worker runs it like an analyst's."""
    incident = _incident(store, user, address, settings)
    if (
        incident.compromised
        and incident.stolen_drops > 0
        and not (incident.trace_id or incident.trace_pending)
    ):
        store.create_trace(
            user.id, address, XRP, incident.stolen_drops, incident.first_theft_ledger or 1
        )
    return redirect(f"/wallets/{address}/recover")
