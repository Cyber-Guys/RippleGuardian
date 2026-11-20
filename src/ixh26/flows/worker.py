"""The monitor worker: WebSocket stream for live alerts, polling for catch-up, trace jobs."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from ixh26 import config
from ixh26.flows.monitor import Monitor
from ixh26.flows.trace import run_trace_job
from ixh26.ledger.client import XrplReader, XrplStream
from ixh26.store.repo import Store

log = logging.getLogger(__name__)

EARLIEST = -1  # account_tx: earliest ledger the server still has


async def catch_up(reader: XrplReader, monitor: Monitor) -> None:
    """Process everything since each wallet's cursor. New wallets backfill without alerts."""
    current = await reader.current_ledger()
    for address in monitor.store.watched_addresses():
        cursor = monitor.store.cursor(address)
        start = EARLIEST if cursor is None else cursor + 1
        if start > current:
            continue
        for activity in await reader.account_activity(
            address, from_ledger=start, to_ledger=current
        ):
            monitor.process(activity, notify=cursor is not None)
        monitor.store.set_cursor(address, current)


async def poll_loop(reader: XrplReader, monitor: Monitor, interval: int) -> None:
    while True:
        try:
            await catch_up(reader, monitor)
        except Exception:
            log.exception("catch-up failed; retrying in %ss", interval)
        await asyncio.sleep(interval)


async def trace_loop(
    reader: XrplReader, monitor: Monitor, settings: config.Settings, interval: float = 2.0
) -> None:
    while True:
        for row in monitor.store.pending_traces():
            await run_trace_job(reader, monitor, row, settings)
        await asyncio.sleep(interval)


async def stream_loop(stream: XrplStream, monitor: Monitor, refresh_s: float = 5.0) -> None:
    """Subscribe to the watched set; resubscribe when it changes or the socket drops."""
    backoff = 1.0
    while True:
        accounts = sorted(monitor.store.watched_addresses())
        if not accounts:
            await asyncio.sleep(refresh_s)
            continue

        async def consume(watched: list[str]) -> None:
            async for activity in stream.watch(watched):
                # live txs only alert wallets whose backfill already ran (cursor set)
                notify = any(monitor.store.cursor(a) is not None for a in watched)
                monitor.process(activity, notify=notify)

        task = asyncio.create_task(consume(accounts))
        try:
            while not task.done() and sorted(monitor.store.watched_addresses()) == accounts:
                await asyncio.wait({task}, timeout=refresh_s)
            if task.done():
                task.result()  # re-raise socket errors
                log.warning("stream closed by server; resubscribing")
            backoff = 1.0
        except Exception:
            log.exception("stream failed; reconnecting in %.0fs", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task


async def run(settings: config.Settings) -> None:
    store = Store.from_url(settings.database_url)
    reader = XrplReader(settings.network.json_rpc_url)
    stream = XrplStream(settings.network.websocket_url)
    monitor = Monitor(store)
    log.info("worker started on %s", settings.network.name)
    await asyncio.gather(
        poll_loop(reader, monitor, settings.poll_interval_s),
        trace_loop(reader, monitor, settings),
        stream_loop(stream, monitor),
    )
