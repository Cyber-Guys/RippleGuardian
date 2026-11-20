"""Trace job: fetch the funds graph hop by hop from the ledger, run haircut taint, store it."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from ixh26 import config
from ixh26.contracts import (
    AccountActivity,
    Alert,
    AlertKind,
    AlertSeverity,
    TraceParams,
    TraceResult,
    Transfer,
)
from ixh26.core.taint import trace
from ixh26.flows.monitor import Monitor, fmt_amount, short
from ixh26.store.models import TraceRow
from ixh26.store.repo import Store, asset_of

log = logging.getLogger(__name__)


class TraceReader(Protocol):
    async def account_activity(
        self, account: str, *, from_ledger: int, to_ledger: int | None = None
    ) -> list[AccountActivity] | Any: ...

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


async def build_trace(
    reader: TraceReader, monitor: Monitor, params: TraceParams
) -> tuple[TraceResult, list[str]]:
    """Expand the frontier one hop at a time until no new tainted account appears."""
    store = monitor.store
    labels = store.labels()
    fetched: set[str] = set()
    transfers: set[Transfer] = set()
    opening: dict[str, Decimal] = {}
    notes: list[str] = []
    frontier = {params.origin}
    result = trace(params, ())
    for _ in range(params.max_hops + 1):
        for account in sorted(frontier):
            for activity in await reader.account_activity(account, from_ledger=params.start_ledger):
                monitor.process(activity, notify=False)  # keeps history for the detectors
                transfers.update(activity.transfers)
            if params.asset.is_xrp and account != params.origin:
                try:
                    opening[account] = await reader.xrp_balance(account, params.start_ledger - 1)
                except RuntimeError as exc:  # history pruned on public nodes: say so in the result
                    notes.append(f"opening balance of {account} unknown ({exc}); assumed 0")
            fetched.add(account)
        result = trace(params, transfers, opening_balances=opening, labels=labels)
        frontier = {e.transfer.destination for e in result.edges} - fetched - labels.keys()
        if not frontier:
            break
    monitor.run_detectors(fetched)
    return result, notes


def result_to_json(
    result: TraceResult, notes: list[str], settings: config.Settings
) -> dict[str, Any]:
    tx_url = settings.network.explorer_tx_url
    p = result.params
    return {
        "params": {
            "origin": p.origin,
            "asset": str(p.asset),
            "stolen": fmt_amount_value(p.asset.is_xrp, p.stolen_value, p.asset.currency),
            "start_ledger": p.start_ledger,
            "min_ratio": str(p.min_ratio),
            "max_hops": p.max_hops,
        },
        "edges": [
            {
                "hop": e.hop,
                "tx_hash": e.transfer.tx_hash,
                "explorer_url": tx_url.format(hash=e.transfer.tx_hash),
                "source": e.transfer.source,
                "destination": e.transfer.destination,
                "destination_tag": e.transfer.destination_tag,
                "amount": fmt_amount(e.transfer.amount),
                "taint": fmt_amount_value(p.asset.is_xrp, e.taint_value, p.asset.currency),
                "taint_ratio": f"{e.taint_ratio:.4f}",
                "close_time": e.transfer.close_time.isoformat(),
            }
            for e in result.edges
        ],
        "sinks": [
            {
                "address": s.address,
                "destination_tag": s.destination_tag,
                "taint": fmt_amount_value(p.asset.is_xrp, s.taint_value, p.asset.currency),
                "share": f"{s.taint_value / p.stolen_value:.4f}",
                "hop": s.hop,
                "label": s.label.name if s.label else None,
                "label_kind": s.label.kind.value if s.label else None,
            }
            for s in result.sinks
        ],
        "truncated": result.truncated,
        "computed_at": result.computed_at.isoformat(),
        "disclaimer": result.disclaimer,
        "notes": notes,
    }


def fmt_amount_value(is_xrp: bool, value: Decimal, currency: str) -> str:
    if is_xrp:
        return f"{(value / 1_000_000).quantize(Decimal('0.000001')).normalize():f} XRP"
    return f"{value.normalize():f} {currency}"


def alert_victims(store: Store, result: TraceResult) -> None:
    """Tell the owners of the robbed wallet where labelled entities received their funds."""
    now = datetime.now(UTC)
    p = result.params
    for sink in result.sinks:
        if sink.label is None:
            continue
        edge = next(
            e
            for e in result.edges
            if e.transfer.destination == sink.address
            and e.transfer.destination_tag == sink.destination_tag
        )
        tag = f" with destination tag {sink.destination_tag}" if sink.destination_tag else ""
        value = fmt_amount_value(p.asset.is_xrp, sink.taint_value, p.asset.currency)
        message = (
            f"Traced {value} of your stolen funds to {sink.label.name} "
            f"({short(sink.address)}){tag}. Share this with the exchange and the police."
        )
        alert = Alert(
            p.origin,
            AlertKind.TAINT_AT_EXCHANGE,
            AlertSeverity.CRITICAL,
            edge.transfer.tx_hash,
            message,
            now,
        )
        for wallet in store.watchers(p.origin):
            store.add_alert(wallet.user_id, alert)


async def run_trace_job(
    reader: TraceReader, monitor: Monitor, row: TraceRow, settings: config.Settings
) -> None:
    """Run one pending trace; the row ends ``done`` with a result or ``failed`` with the error."""
    store = monitor.store
    try:
        result, notes = await build_trace(reader, monitor, params_for(row, settings))
    except Exception as exc:
        log.exception("trace %s failed", row.id)
        store.finish_trace(row.id, error=f"{type(exc).__name__}: {exc}")
        return
    store.finish_trace(row.id, result=result_to_json(result, notes, settings))
    alert_victims(store, result)
    log.info("trace %s done: %d edges, %d sinks", row.id, len(result.edges), len(result.sinks))


__all__ = ["build_trace", "fmt_amount", "result_to_json", "run_trace_job"]
