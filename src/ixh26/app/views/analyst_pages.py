"""Analysts: detector findings and fund traces."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response

from ixh26.app import api
from ixh26.app.auth import StoreDep
from ixh26.app.charts import flow_graph
from ixh26.app.views.common import PageAnalyst, amount_text, redirect, render
from ixh26.app.views.models import analyst_overview
from ixh26.store.repo import Store, recent_transfers

router = APIRouter(include_in_schema=False)


@router.get("/analyst")
def dashboard(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    overview = analyst_overview(store)
    latest = overview["latest_trace"]
    flow = flow_graph(latest.result) if latest and "stolen_value" in latest.result["params"] else ""
    return render(request, "analyst/dashboard.html", user, o=overview, flow=flow)


@router.get("/ui/live")
def live_fragment(request: Request, user: PageAnalyst, store: StoreDep) -> Response:
    """Newest transfers the worker stored, refreshed every few seconds on the dashboard."""
    return render(
        request,
        "partials/live.html",
        user,
        transfers=recent_transfers(store, 8),
        flagged=store.flagged_targets(),
        amount_text=amount_text,
    )


@router.get("/ui/flow/{trace_id}")
def flow_fragment(request: Request, trace_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    """The animated graph alone, so the Replay button can restart its animation."""
    row = store.trace(trace_id)
    if row is None or not row.result:
        raise HTTPException(404, "no finished trace")
    return render(
        request, "partials/flow.html", user, flow=flow_graph(row.result), trace_id=trace_id
    )


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
        "flow": flow_graph(result) if result and "stolen_value" in result["params"] else "",
        "flagged": store.flagged_targets(),
        "categories": api.FLAG_CATEGORIES,
    }


@router.get("/analyst/traces/{trace_id}")
def trace_page(request: Request, trace_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    return render(request, "analyst/trace.html", user, **_trace_ctx(store, trace_id))


@router.get("/ui/traces/{trace_id}")
def trace_fragment(request: Request, trace_id: int, user: PageAnalyst, store: StoreDep) -> Response:
    return render(request, "partials/trace_body.html", user, **_trace_ctx(store, trace_id))
