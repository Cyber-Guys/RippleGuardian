"""Analysts: detector findings and fund traces."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response

from ixh26.app import api
from ixh26.app.auth import StoreDep
from ixh26.app.views.common import PageAnalyst, redirect, render
from ixh26.app.views.models import ribbon
from ixh26.store.repo import Store

router = APIRouter(include_in_schema=False)


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
