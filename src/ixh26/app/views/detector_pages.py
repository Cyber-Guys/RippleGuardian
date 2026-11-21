"""Analyst page for the shared detector thresholds. Uses the same typed service as the JSON API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import ValidationError

from ixh26.app.auth import StoreDep
from ixh26.app.views.common import PageAnalyst, redirect, render
from ixh26.flows.detection_settings import (
    DetectorSettingsUpdate,
    DetectorThresholds,
    StaleDetectorSettings,
    read_detector_settings,
    save_detector_settings,
)

router = APIRouter(include_in_schema=False)

INT_FIELDS = {
    "funnel_window_seconds",
    "funnel_min_senders",
    "wash_window_seconds",
    "wash_min_pair_fills",
    "wash_min_fills",
    "wash_max_wallets",
    "liquidity_window_seconds",
    "liquidity_min_buyers",
    "takeover_window_seconds",
}

# (group title, live data available?, [(field, label, unit)])
GROUPS: list[tuple[str, bool, list[tuple[str, str, str]]]] = [
    (
        "Funds funnel",
        True,
        [
            ("funnel_window_seconds", "Lookback for credits and shared destination", "seconds"),
            ("funnel_min_senders", "Distinct wallets forwarding to one route", "wallets, min 2"),
            ("funnel_min_fraction", "Matched share of credits and debit", "0 to 1"),
        ],
    ),
    (
        "Wash trading",
        False,
        [
            ("wash_window_seconds", "Executed trading lookback", "seconds"),
            ("wash_min_pair_fills", "Fills between two wallets to link them", "fills, min 2"),
            ("wash_min_fills", "Fills within the group", "fills, min 2"),
            ("wash_max_wallets", "Wallets in the group, at most", "wallets, min 2"),
            ("wash_max_net_ratio", "Net-to-gross ratio, at most", "0 to 1"),
            ("wash_min_market_share", "Share of market volume inside the group", "0 to 1"),
        ],
    ),
    (
        "Liquidity withdrawal",
        False,
        [
            ("liquidity_window_seconds", "Lookback for new buyers", "seconds"),
            ("liquidity_min_buyers", "New buyers before the withdrawal", "buyers, min 1"),
            (
                "liquidity_min_pool_drops",
                "XRP in the pool before the withdrawal",
                "drops (1 XRP = 1,000,000)",
            ),
            ("liquidity_min_drop", "Share of XRP reserves removed", "0 to 1"),
            ("liquidity_sale_size", "Token amount for the sale quote", "tokens"),
        ],
    ),
    (
        "Wallet takeover",
        True,
        [
            ("takeover_window_seconds", "Time allowed after a signing change", "seconds"),
            (
                "takeover_min_outflow",
                "Share of starting balance sent to new destinations",
                "0 to 1",
            ),
        ],
    ),
]


def strings(thresholds: DetectorThresholds) -> dict[str, str]:
    """Thresholds as the exact strings the form shows and the API accepts."""
    return {k: str(v) for k, v in thresholds.model_dump(mode="json").items()}


def field_errors(exc: ValidationError) -> dict[str, str]:
    """Map pydantic locations (``thresholds.<field>``) onto the form field that caused them."""
    out: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(part) for part in err["loc"]]
        key = loc[-1] if loc and loc[-1] != "thresholds" else "_"
        out.setdefault(key, err["msg"].removeprefix("Value error, "))
    return out


def build_update(version: int, form: dict[str, str]) -> DetectorSettingsUpdate:
    thresholds: dict[str, Any] = {
        k: (int(v) if k in INT_FIELDS and v.strip().lstrip("-").isdigit() else v.strip())
        for k, v in form.items()
    }
    return DetectorSettingsUpdate.model_validate({"version": version, "thresholds": thresholds})


def page(
    request: Request,
    user: Any,
    store: Any,
    *,
    draft: dict[str, str] | None = None,
    errors: dict[str, str] | None = None,
    conflict: bool = False,
    saved: bool = False,
    status_code: int = 200,
) -> Response:
    current = read_detector_settings(store)
    latest = strings(current.thresholds)
    return render(
        request,
        "analyst/settings.html",
        user,
        status_code,
        groups=GROUPS,
        view=current,
        values=draft if draft is not None else latest,
        latest=latest,
        errors=errors or {},
        conflict=conflict,
        saved=saved,
    )


@router.get("/analyst/settings")
def settings_page(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    return page(request, user, store, saved=request.query_params.get("saved") == "1")


async def _form(request: Request) -> dict[str, str]:
    data = await request.form()
    return {str(k): str(v) for k, v in data.items()}


def _save(request: Request, user: Any, store: Any, form: dict[str, str]) -> Response:
    version = int(form.pop("version", "0") or 0)
    try:
        save_detector_settings(store, build_update(version, form), user.id)
    except ValidationError as exc:
        return page(request, user, store, draft=form, errors=field_errors(exc), status_code=422)
    except StaleDetectorSettings:
        return page(request, user, store, draft=form, conflict=True, status_code=409)
    return redirect("/analyst/settings?saved=1")


@router.post("/analyst/settings")
async def settings_save(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    return _save(request, user, store, await _form(request))


@router.post("/analyst/settings/restore")
async def settings_restore(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    """Fill the form with the server's defaults and save them against the version on screen."""
    form = await _form(request)
    defaults = strings(read_detector_settings(store).defaults)
    return _save(request, user, store, {**defaults, "version": form.get("version", "0")})
