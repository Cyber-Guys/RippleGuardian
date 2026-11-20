"""Haircut taint propagation over a transfer graph. Pure: no DB, no network, no xrpl.

Model: every account holds a balance and a tainted share of it. An outflow carries taint in
proportion ``taint / balance`` (the "haircut"). The origin's first outflows are the theft and
carry taint until ``stolen_value`` is used up. Propagation stops below the threshold
(``min_ratio`` of the theft, and ``min_value`` for XRP) or beyond ``max_hops``. Labelled
accounts (exchanges, issuers...) absorb taint: they become sinks, keyed by destination tag.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal

from ixh26.contracts import (
    AccountLabel,
    TaintEdge,
    TaintSink,
    TraceParams,
    TraceResult,
    Transfer,
)


def threshold(params: TraceParams) -> Decimal:
    ratio_floor = params.min_ratio * params.stolen_value
    return max(ratio_floor, params.min_value) if params.asset.is_xrp else ratio_floor


def trace(
    params: TraceParams,
    transfers: Iterable[Transfer],
    *,
    opening_balances: Mapping[str, Decimal] | None = None,
    labels: Mapping[str, AccountLabel] | None = None,
    now: datetime | None = None,
) -> TraceResult:
    """Propagate ``params.stolen_value`` from ``params.origin`` through ``transfers``.

    ``opening_balances`` are balances right before ``start_ledger``; unknown accounts start at
    0, and an outflow larger than the known balance is assumed to draw on untainted funds.
    """
    labels = labels or {}
    floor = threshold(params)
    balance: defaultdict[str, Decimal] = defaultdict(Decimal, opening_balances or {})
    taint: defaultdict[str, Decimal] = defaultdict(Decimal)
    hop: dict[str, int] = {params.origin: 0}
    taint[params.origin] = params.stolen_value
    edges: list[TaintEdge] = []
    truncated = False

    ordered = sorted(
        {
            t
            for t in transfers
            if t.amount.asset == params.asset
            and t.ledger_index >= params.start_ledger
            and t.source != t.destination
            and t.amount.value > 0
        },
        key=lambda t: (t.order_key, t.tx_hash, t.destination),
    )
    for t in ordered:
        src, dst, amount = t.source, t.destination, t.amount.value
        carried = Decimal(0)
        if taint[src] > 0 and src not in labels:
            if src == params.origin:
                carried = min(amount, taint[src])
            else:
                carried = min(taint[src], amount * taint[src] / max(balance[src], amount))
        balance[src] = max(balance[src] - amount, Decimal(0))
        balance[dst] += amount
        if carried <= 0:
            continue
        taint[src] -= carried
        next_hop = hop[src] + 1
        if carried < floor or next_hop > params.max_hops:
            truncated = True
            continue
        edges.append(TaintEdge(t, next_hop, carried, carried / amount))
        taint[dst] += carried
        hop[dst] = min(hop.get(dst, next_hop), next_hop)

    return TraceResult(
        params=params,
        edges=tuple(edges),
        sinks=_sinks(params.origin, edges, taint, hop, labels, floor),
        truncated=truncated,
        computed_at=now or datetime.now(UTC),
    )


def _sinks(
    origin: str,
    edges: list[TaintEdge],
    taint: Mapping[str, Decimal],
    hop: Mapping[str, int],
    labels: Mapping[str, AccountLabel],
    floor: Decimal,
) -> tuple[TaintSink, ...]:
    """Labelled accounts per destination tag (what reached them), others by remaining taint."""
    at_label: defaultdict[tuple[str, int | None], Decimal] = defaultdict(Decimal)
    label_hop: dict[tuple[str, int | None], int] = {}
    for e in edges:
        dst = e.transfer.destination
        if dst in labels:
            key = (dst, e.transfer.destination_tag)
            at_label[key] += e.taint_value
            label_hop[key] = min(label_hop.get(key, e.hop), e.hop)
    sinks = [
        TaintSink(address, tag, value, label_hop[(address, tag)], labels[address])
        for (address, tag), value in at_label.items()
    ]
    sinks += [
        TaintSink(address, None, value, hop[address])
        for address, value in taint.items()
        if address != origin and address not in labels and value >= floor
    ]
    return tuple(sorted(sinks, key=lambda s: (-s.taint_value, s.address, s.destination_tag or 0)))
