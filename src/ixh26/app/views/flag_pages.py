"""Analyst flags: everyone reads them, analysts write them."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response

from ixh26.app import api
from ixh26.app.auth import StoreDep
from ixh26.app.views.common import PageAnalyst, PageUser, redirect, render

router = APIRouter(include_in_schema=False)


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
