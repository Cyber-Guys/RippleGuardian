"""Shared by every page: auth guards, rendering, formatting helpers for templates."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ixh26 import config
from ixh26.app import auth
from ixh26.app.auth import CurrentUser
from ixh26.contracts import Transfer
from ixh26.store.repo import Store

HERE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=HERE / "templates")
XRP1 = Decimal(1_000_000)


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
