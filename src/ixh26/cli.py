"""Command-line entry points used by the Makefile and the Docker services.

Heavy modules are imported lazily so that ``ixh26 smoke`` works on the bare skeleton and a
missing component fails loudly with a clear message instead of a traceback at import time.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from ixh26 import __version__, config
from ixh26.contracts import XRP, Amount, Transfer, TransferKind

log = logging.getLogger("ixh26")


def _load(target: str) -> Any:
    """Import ``module:attr``; raise SystemExit with a readable message if it is not built."""
    module_name, _, attr = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name and module_name.startswith(exc.name):
            raise SystemExit(f"{module_name} is not implemented yet (see tasks/)") from exc
        raise
    return getattr(module, attr)


def _skeleton_smoke(settings: config.Settings) -> None:
    t = Transfer(
        tx_hash="0" * 64,  # placeholder for a type check only, never shown as evidence
        ledger_index=1,
        tx_index=0,
        close_time=datetime.now(UTC),
        kind=TransferKind.PAYMENT,
        source="rSource",
        destination="rDest",
        amount=Amount(XRP, Decimal(1_000_000)),
    )
    assert replace(t, tx_index=1).order_key > t.order_key
    log.info("skeleton smoke ok (network=%s)", settings.network.name)


def cmd_smoke(settings: config.Settings) -> int:
    """Headless run of the demo path. Uses ``ixh26.flows.smoke:run`` once T-004 provides it."""
    try:
        run: Callable[[config.Settings], int] = _load("ixh26.flows.smoke:run")
    except SystemExit:
        _skeleton_smoke(settings)
        return 0
    return run(settings)


def cmd_api(settings: config.Settings, host: str, port: int) -> int:
    uvicorn = importlib.import_module("uvicorn")
    _load("ixh26.app.main:app")  # fail early and clearly if the API is not built yet
    uvicorn.run("ixh26.app.main:app", host=host, port=port, log_level=settings.log_level.lower())
    return 0


def cmd_worker(settings: config.Settings) -> int:
    run = _load("ixh26.flows.worker:run")
    asyncio.run(run(settings))
    return 0


def cmd_config(settings: config.Settings) -> int:
    """Print non-secret settings and whether secrets are present (never their values)."""
    print(f"ixh26 {__version__}")
    print(f"network          {settings.network.name} ({settings.network.json_rpc_url})")
    print(f"source_tag       {settings.source_tag}")
    print(f"taint threshold  {settings.taint_min_ratio} / {settings.taint_min_drops} drops")
    print(f"max hops         {settings.trace_max_hops}")
    try:
        config.jwt_secret()
        print("JWT_SECRET       set")
    except config.ConfigError:
        print("JWT_SECRET       MISSING")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ixh26", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("smoke", help="fast headless run of the demo path")
    api = sub.add_parser("api", help="run the FastAPI server")
    api.add_argument("--host", default="0.0.0.0")
    api.add_argument("--port", type=int, default=8000)
    sub.add_parser("worker", help="run the wallet monitor / trace worker")
    sub.add_parser("config", help="show effective non-secret configuration")
    args = parser.parse_args(argv)

    settings = config.load_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    if args.cmd == "smoke":
        return cmd_smoke(settings)
    if args.cmd == "api":
        return cmd_api(settings, args.host, args.port)
    if args.cmd == "worker":
        return cmd_worker(settings)
    return cmd_config(settings)


if __name__ == "__main__":
    sys.exit(main())
