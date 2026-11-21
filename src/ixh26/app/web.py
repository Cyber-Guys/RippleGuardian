"""Web UI: server-rendered Jinja2 + HTMX (D-006). One app, two roles (D-005).

Users see their wallets, statement, notifications and the analysts' public flags.
Analysts see detector findings, run haircut traces and flag accounts. Nothing here signs
anything or talks to XRPL: pages read the store, and the worker does the ledger work.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from ixh26.app import auth
from ixh26.app.views import analyst_pages, auth_pages, flag_pages, user_pages
from ixh26.app.views.common import HERE, AnalystOnly, LoginRequired, redirect, render

ROUTERS = (auth_pages.router, user_pages.router, flag_pages.router, analyst_pages.router)


def mount(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    for router in ROUTERS:
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
