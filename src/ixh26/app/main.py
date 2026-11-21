"""FastAPI application: JSON API under /api and the web UI (when present)."""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ixh26 import __version__, config
from ixh26.app import api
from ixh26.store.repo import Store


def create_app(settings: config.Settings | None = None, store: Store | None = None) -> FastAPI:
    settings = settings or config.load_settings()
    config.jwt_secret()  # fail at startup, not at first login

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if getattr(app.state, "store", None) is None:
            app.state.store = Store.from_url(settings.database_url)
        yield

    app = FastAPI(title="Ripple Guardian", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.include_router(api.router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "network": settings.network.name}

    try:  # the web UI (T-008) mounts itself on top of the API when it exists
        web = importlib.import_module("ixh26.app.web")
    except ModuleNotFoundError as exc:
        if exc.name != "ixh26.app.web":
            raise
    else:
        web.mount(app)
    return app


def __getattr__(name: str) -> FastAPI:
    """``ixh26.app.main:app`` for uvicorn, built lazily so importing this module is cheap."""
    if name == "app":
        return create_app()
    raise AttributeError(name)
