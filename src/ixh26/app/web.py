"""Web UI: server-rendered Jinja2 + HTMX (D-006). One app, two roles (D-005).

Users: their wallets, statement, notifications and the analysts' public flags.
Analysts: detector findings, haircut traces, flagging. Nothing here signs or talks to XRPL.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ixh26 import config
from ixh26.app import api, auth
from ixh26.app.auth import CurrentUser, SettingsDep, StoreDep
from ixh26.contracts import AlertKind, Transfer
from ixh26.store.repo import Store

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")
router = APIRouter(include_in_schema=False)

XRP1 = Decimal(1_000_000)
COMPROMISED_KINDS = {AlertKind.SECURITY_CHANGE.value, AlertKind.TAINT_AT_EXCHANGE.value}


class LoginRequired(Exception):
    """Raised by page dependencies; turned into a redirect to /login."""


class AnalystOnly(Exception):
    """Raised when a user opens an analyst page; rendered as a 403 page."""


def page_user(user: Annotated[CurrentUser | None, Depends(auth.optional_user)]) -> CurrentUser:
    if user is None:
        raise LoginRequired
    return user


def page_analyst(user: Annotated[CurrentUser, Depends(page_user)]) -> CurrentUser:
    if not user.is_analyst:
        raise AnalystOnly
    return user


PageUser = Annotated[CurrentUser, Depends(page_user)]
PageAnalyst = Annotated[CurrentUser, Depends(page_analyst)]


# --- formatting helpers exposed to templates ----------------------------------------------------


def short(value: str, head: int = 6, tail: int = 4) -> str:
    return value if len(value) <= head + tail + 1 else f"{value[:head]}…{value[-tail:]}"


def xrp(drops: Decimal | str | int) -> str:
    value = (Decimal(drops) / XRP1).quantize(Decimal("0.000001")).normalize()
    return f"{value:,f}"


def amount_text(t: Transfer) -> str:
    if t.amount.asset.is_xrp:
        return f"{xrp(t.amount.value)} XRP"
    return f"{t.amount.value.normalize():f} {t.amount.asset.currency}"


def explorer(settings: config.Settings) -> dict[str, Any]:
    tx_url = settings.network.explorer_tx_url
    account_url = tx_url.replace("/transactions/{hash}", "/accounts/{address}")
    return {
        "tx_url": lambda h: tx_url.format(hash=h),
        "account_url": lambda a: account_url.format(address=a),
    }


def render(
    request: Request, name: str, user: CurrentUser | None, status_code: int = 200, **ctx: Any
) -> HTMLResponse:
    settings: config.Settings = request.app.state.settings
    store: Store = request.app.state.store
    base = {
        "user": user,
        "path": request.url.path,
        "network": settings.network.name,
        "unread": store.unread_count(user.id) if user else 0,
        "short": short,
        "xrp": xrp,
        **explorer(settings),
    }
    return templates.TemplateResponse(request, name, {**base, **ctx}, status_code=status_code)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


# --- view models --------------------------------------------------------------------------------


@dataclass(frozen=True)
class WalletState:
    state: str  # safe | attention | compromised
    headline: str
    detail: str


def wallet_state(store: Store, user_id: int, address: str, flagged: dict[str, Any]) -> WalletState:
    unread = [a for a in store.alerts(user_id, unread_only=True) if a.wallet == address]
    if any(a.kind in COMPROMISED_KINDS for a in unread):
        return WalletState(
            "compromised",
            "Possible compromise",
            "Signing keys changed or funds were traced to an exchange. Review the notifications.",
        )
    if address in flagged:
        flag = flagged[address]
        return WalletState(
            "attention", "Flagged by an analyst", f"Category {flag.category}: {flag.reason}"
        )
    if any(a.kind == AlertKind.FLAGGED_COUNTERPARTY.value for a in unread):
        return WalletState(
            "attention",
            "Contact with a flagged account",
            "This wallet sent to or received from an account flagged by an analyst.",
        )
    return WalletState("safe", "All clear", "No unread warnings for this wallet.")


@dataclass
class AssetStatement:
    asset: str
    received: Decimal = Decimal(0)
    sent: Decimal = Decimal(0)
    count: int = 0

    @property
    def net(self) -> Decimal:
        return self.received - self.sent


def statement(address: str, transfers: list[Transfer]) -> dict[str, Any]:
    per_asset: dict[str, AssetStatement] = {}
    counterparties: set[str] = set()
    for t in transfers:
        is_xrp = t.amount.asset.is_xrp
        key = "XRP" if is_xrp else f"{t.amount.asset.currency}"
        row = per_asset.setdefault(key, AssetStatement(key))
        value = t.amount.value / XRP1 if is_xrp else t.amount.value
        if t.destination == address:
            row.received += value
            counterparties.add(t.source)
        if t.source == address:
            row.sent += value
            counterparties.add(t.destination)
        row.count += 1
    return {
        "assets": list(per_asset.values()),
        "counterparties": len(counterparties - {address}),
        "first": transfers[0].close_time if transfers else None,
        "last": transfers[-1].close_time if transfers else None,
    }


def number_in(text: str) -> Decimal:
    """'95.5 XRP' -> Decimal('95.5') (trace results store display strings)."""
    try:
        return Decimal(text.split()[0].replace(",", ""))
    except (InvalidOperation, IndexError):
        return Decimal(0)


def ribbon(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Columns by hop: who held how much of the stolen value, as a share of the theft."""
    stolen = number_in(result["params"]["stolen"]) or Decimal(1)
    unit = result["params"]["stolen"].split()[-1]
    sinks = {(s["address"], s["destination_tag"]): s for s in result["sinks"]}
    sink_addresses = {s["address"] for s in result["sinks"]}
    columns: dict[int, dict[tuple[str, int | None], Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    for e in result["edges"]:
        tag = e["destination_tag"] if (e["destination"], e["destination_tag"]) in sinks else None
        columns[e["hop"]][(e["destination"], tag)] += number_in(e["taint"])
    out = [
        {
            "hop": 0,
            "nodes": [
                {
                    "address": result["params"]["origin"],
                    "tag": None,
                    "kind": "origin",
                    "value": f"{stolen.normalize():f} {unit}",
                    "share": 100,
                    "label": "Victim",
                }
            ],
        }
    ]
    for hop in sorted(columns):
        nodes = []
        for (address, tag), value in sorted(columns[hop].items(), key=lambda kv: -kv[1]):
            sink = sinks.get((address, tag))
            nodes.append(
                {
                    "address": address,
                    "tag": tag,
                    "kind": "sink" if address in sink_addresses else "hop",
                    "value": f"{value.quantize(Decimal('0.000001')).normalize():f} {unit}",
                    "share": float(min(value / stolen * 100, Decimal(100))),
                    "label": sink["label"] if sink and sink["label"] else None,
                }
            )
        out.append({"hop": hop, "nodes": nodes})
    return out


# --- auth pages ---------------------------------------------------------------------------------


@router.get("/login")
def login_page(request: Request) -> HTMLResponse:
    return render(request, "login.html", None)


@router.post("/login")
def login_submit(
    request: Request,
    store: StoreDep,
    settings: SettingsDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    try:
        user = auth.authenticate(store, username.strip(), password)
    except HTTPException as exc:
        return render(request, "login.html", None, 401, error=exc.detail, username=username)
    response = redirect("/")
    response.set_cookie(
        auth.COOKIE, auth.issue_token(user, settings), httponly=True, samesite="lax"
    )
    return response


@router.get("/register")
def register_page(request: Request) -> HTMLResponse:
    return render(request, "register.html", None)


@router.post("/register")
def register_submit(
    request: Request,
    store: StoreDep,
    settings: SettingsDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    username = username.strip()
    try:
        auth.validate_credentials(username, password)
        if store.user_by_name(username):
            raise HTTPException(409, "That username is taken. Pick another one.")
    except HTTPException as exc:
        return render(request, "register.html", None, 422, error=exc.detail, username=username)
    row = store.create_user(username, auth.hash_password(password))
    response = redirect("/")
    user = CurrentUser(row.id, row.username, row.role)
    response.set_cookie(
        auth.COOKIE, auth.issue_token(user, settings), httponly=True, samesite="lax"
    )
    return response


@router.post("/logout")
def logout() -> Response:
    response = redirect("/login")
    response.delete_cookie(auth.COOKIE)
    return response


# --- user pages ---------------------------------------------------------------------------------


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


# --- flags (everyone reads, analysts write) -----------------------------------------------------


@router.get("/flags")
def flags_page(request: Request, user: PageUser, store: StoreDep, q: str = "") -> Response:
    q = q.strip()
    flags = store.flags()
    match = [f for f in flags if f[0].target.upper() == q.upper()] if q else None
    return render(
        request,
        "flags.html",
        user,
        flags=flags,
        q=q,
        match=match,
        categories=api.FLAG_CATEGORIES,
        error=request.query_params.get("error"),
    )


@router.post("/flags")
def flag_create(
    user: PageAnalyst,
    store: StoreDep,
    target: Annotated[str, Form()],
    reason: Annotated[str, Form()],
    target_type: Annotated[str, Form()] = "account",
    category: Annotated[str, Form()] = "other",
    finding_id: Annotated[int | None, Form()] = None,
    back: Annotated[str, Form()] = "/flags",
) -> Response:
    back = back if back.startswith("/") and not back.startswith("//") else "/flags"
    try:
        api.add_flag(
            store,
            user.id,
            api.FlagIn(
                target_type=target_type,
                target=target,
                category=category,
                reason=reason.strip(),
                finding_id=finding_id,
            ),
        )
    except (HTTPException, ValueError) as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else "Reason: 3-280 characters."
        return redirect(f"{back}?error={detail}")
    return redirect(back)


@router.post("/flags/{flag_id}/revoke")
def flag_revoke(flag_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    store.revoke_flag(flag_id)
    return redirect("/flags")


# --- analyst pages ------------------------------------------------------------------------------


@router.get("/analyst/findings")
def findings_page(
    request: Request, user: PageAnalyst, store: StoreDep, status: str = "open"
) -> Response:
    status = status if status in ("open", "flagged", "dismissed", "all") else "open"
    return render(
        request,
        "analyst/findings.html",
        user,
        findings=store.findings(None if status == "all" else status),
        status=status,
        categories=api.FLAG_CATEGORIES,
        flagged=store.flagged_targets(),
        error=request.query_params.get("error"),
    )


@router.post("/analyst/findings/{finding_id}/dismiss")
def finding_dismiss(finding_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    store.set_finding_status(finding_id, "dismissed")
    return redirect("/analyst/findings")


@router.get("/analyst/traces")
def traces_page(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    return render(
        request,
        "analyst/traces.html",
        user,
        traces=store.traces(),
        error=request.query_params.get("error"),
        origin=request.query_params.get("origin", ""),
    )


@router.post("/analyst/traces")
def trace_create(
    user: PageAnalyst,
    store: StoreDep,
    origin: Annotated[str, Form()],
    stolen_xrp: Annotated[str, Form()],
    start_ledger: Annotated[int, Form()],
) -> Response:
    try:
        trace_id = api.start_trace(
            store,
            user.id,
            api.TraceIn(origin=origin, stolen_xrp=stolen_xrp, start_ledger=start_ledger),
        )
    except (HTTPException, ValueError) as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else "Check the start ledger."
        return redirect(f"/analyst/traces?error={detail}")
    return redirect(f"/analyst/traces/{trace_id}")


def _trace_ctx(store: Store, trace_id: int) -> dict[str, Any]:
    row = store.trace(trace_id)
    if row is None:
        raise HTTPException(404, "no such trace")
    result = row.result or None
    return {
        "trace": row,
        "result": result,
        "ribbon": ribbon(result) if result else [],
        "flagged": store.flagged_targets(),
        "categories": api.FLAG_CATEGORIES,
    }


@router.get("/analyst/traces/{trace_id}")
def trace_page(request: Request, trace_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    return render(request, "analyst/trace.html", user, **_trace_ctx(store, trace_id))


@router.get("/ui/traces/{trace_id}")
def trace_fragment(request: Request, trace_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    return render(request, "partials/trace_body.html", user, **_trace_ctx(store, trace_id))


# --- mounting -----------------------------------------------------------------------------------


def mount(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    app.include_router(router)

    @app.exception_handler(LoginRequired)
    async def _login(request: Request, exc: LoginRequired) -> Response:
        if request.headers.get("hx-request"):
            return Response(status_code=401, headers={"HX-Redirect": "/login"})
        return redirect("/login")

    @app.exception_handler(AnalystOnly)
    async def _analyst_only(request: Request, exc: AnalystOnly) -> Response:
        user = auth.optional_user(request, request.app.state.store)
        return render(request, "error.html", user, 403, message="This page is for analysts.")
