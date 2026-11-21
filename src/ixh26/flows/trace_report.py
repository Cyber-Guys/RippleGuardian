"""TraceResult -> the JSON stored on the trace row and read by the web pages."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ixh26 import config
from ixh26.contracts import Asset, TaintEdge, TaintSink, TraceResult
from ixh26.core.alerts import DROPS_PER_XRP, amount_text, short


def value_text(asset: Asset, value: Decimal) -> str:
    """Display a taint value in the traced asset: drops become XRP with 6 decimals."""
    if asset.is_xrp:
        xrp = (value / DROPS_PER_XRP).quantize(Decimal("0.000001")).normalize()
        return f"{xrp:f} XRP"
    return f"{value.normalize():f} {asset.currency}"


def edge_json(e: TaintEdge, asset: Asset, tx_url: str) -> dict[str, Any]:
    t = e.transfer
    return {
        "hop": e.hop,
        "tx_hash": t.tx_hash,
        "explorer_url": tx_url.format(hash=t.tx_hash),
        "source": t.source,
        "destination": t.destination,
        "destination_tag": t.destination_tag,
        "amount": amount_text(t.amount),
        "taint": value_text(asset, e.taint_value),
        "taint_value": str(e.taint_value),
        "taint_ratio": f"{e.taint_ratio:.4f}",
        "close_time": t.close_time.isoformat(),
    }


def sink_json(s: TaintSink, asset: Asset, stolen: Decimal) -> dict[str, Any]:
    return {
        "address": s.address,
        "destination_tag": s.destination_tag,
        "taint": value_text(asset, s.taint_value),
        "taint_value": str(s.taint_value),
        "share": f"{s.taint_value / stolen:.4f}",
        "hop": s.hop,
        "label": s.label.name if s.label else None,
        "label_kind": s.label.kind.value if s.label else None,
    }


def trace_report(
    result: TraceResult, notes: list[str], settings: config.Settings
) -> dict[str, Any]:
    p = result.params
    tx_url = settings.network.explorer_tx_url
    return {
        "params": {
            "origin": p.origin,
            "asset": str(p.asset),
            "stolen": value_text(p.asset, p.stolen_value),
            "stolen_value": str(p.stolen_value),
            "start_ledger": p.start_ledger,
            "min_ratio": str(p.min_ratio),
            "max_hops": p.max_hops,
        },
        "edges": [edge_json(e, p.asset, tx_url) for e in result.edges],
        "sinks": [sink_json(s, p.asset, p.stolen_value) for s in result.sinks],
        "truncated": result.truncated,
        "computed_at": result.computed_at.isoformat(),
        "disclaimer": result.disclaimer,
        "notes": notes,
    }


def place_name(sink: TaintSink) -> str:
    """``Exchange (SIMULATED) (rQs8mJ…gqNG)`` for the victim's notification."""
    return f"{sink.label.name if sink.label else 'an unknown account'} ({short(sink.address)})"
