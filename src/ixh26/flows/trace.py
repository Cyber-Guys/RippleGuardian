"""Trace job: fetch the funds graph hop by hop, run haircut taint, store the report.

pending trace row -> build_trace (ledger, one hop at a time) -> trace_report -> row done
                                                              \\-> alert the victim
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from ixh26 import config
from ixh26.contracts import AccountActivity, TraceParams, TraceResult, Transfer
from ixh26.core.alerts import exchange_alert
from ixh26.core.taint import trace
from ixh26.flows.monitor import Monitor
from ixh26.flows.trace_report import place_name, trace_report, value_text
from ixh26.store.models import TraceRow
from ixh26.store.repo import Store, asset_of

log = logging.getLogger(__name__)


class TraceReader(Protocol):
    async def account_activity(
        self, account: str, *, from_ledger: int, to_ledger: int | None = None
    ) -> Sequence[AccountActivity]: ...

    async def xrp_balance(self, account: str, ledger_index: int | str = ...) -> Decimal: ...


def params_for(row: TraceRow, settings: config.Settings) -> TraceParams:
    return TraceParams(
        origin=row.origin,
        asset=asset_of(row.currency, row.issuer),
        stolen_value=Decimal(row.stolen_value),
        start_ledger=row.start_ledger,
        min_ratio=settings.taint_min_ratio,
        min_value=Decimal(settings.taint_min_drops),
        max_hops=settings.trace_max_hops,
    )


async def fetch_account(
    reader: TraceReader, monitor: Monitor, account: str, start_ledger: int
) -> list[Transfer]:
    """All transfers of ``account`` since the theft, also stored for the detectors."""
    transfers: list[Transfer] = []
    for activity in await reader.account_activity(account, from_ledger=start_ledger):
        monitor.process(activity, notify=False)
        transfers.extend(activity.transfers)
    return transfers


async def opening_balance(
    reader: TraceReader, account: str, start_ledger: int, notes: list[str]
) -> Decimal:
    """Balance just before the theft. Public nodes prune history: then assume 0 and say so."""
    try:
        return await reader.xrp_balance(account, start_ledger - 1)
    except RuntimeError as exc:
        notes.append(f"opening balance of {account} unknown ({exc}); assumed 0")
        return Decimal(0)


async def build_trace(
    reader: TraceReader, monitor: Monitor, params: TraceParams
) -> tuple[TraceResult, list[str]]:
    """Expand the frontier one hop at a time until no new tainted account appears."""
    labels = monitor.store.labels()
    fetched: set[str] = set()
    transfers: set[Transfer] = set()
    opening: dict[str, Decimal] = {}
    notes: list[str] = []
    frontier = {params.origin}
    result = trace(params, ())
    for _ in range(params.max_hops + 1):
        for account in sorted(frontier):
            transfers.update(await fetch_account(reader, monitor, account, params.start_ledger))
            if params.asset.is_xrp and account != params.origin:
                opening[account] = await opening_balance(
                    reader, account, params.start_ledger, notes
                )
            fetched.add(account)
        result = trace(params, transfers, opening_balances=opening, labels=labels)
        frontier = {e.transfer.destination for e in result.edges} - fetched - labels.keys()
        if not frontier:
            break
    monitor.run_detectors(fetched)
    return result, notes


def alert_victims(store: Store, result: TraceResult) -> None:
    """Tell the owners of the robbed wallet where known entities received their funds."""
    p = result.params
    now = datetime.now(UTC)
    for sink in (s for s in result.sinks if s.label is not None):
        first_edge = next(
            e
            for e in result.edges
            if (e.transfer.destination, e.transfer.destination_tag)
            == (sink.address, sink.destination_tag)
        )
        alert = exchange_alert(
            p.origin,
            place_name(sink),
            sink.destination_tag,
            value_text(p.asset, sink.taint_value),
            first_edge.transfer.tx_hash,
            now,
        )
        for wallet in store.watchers(p.origin):
            store.add_alert(wallet.user_id, alert)


async def run_trace_job(
    reader: TraceReader, monitor: Monitor, row: TraceRow, settings: config.Settings
) -> None:
    """Run one pending trace; the row ends ``done`` with a report or ``failed`` with the error."""
    store = monitor.store
    try:
        result, notes = await build_trace(reader, monitor, params_for(row, settings))
    except Exception as exc:
        log.exception("trace %s failed", row.id)
        store.finish_trace(row.id, error=f"{type(exc).__name__}: {exc}")
        return
    store.finish_trace(row.id, result=trace_report(result, notes, settings))
    alert_victims(store, result)
    log.info("trace %s done: %d edges, %d sinks", row.id, len(result.edges), len(result.sinks))
