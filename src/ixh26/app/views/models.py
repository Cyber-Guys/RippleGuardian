"""View models: turn stored rows into what a page shows. No HTTP here."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from ixh26.app.views.common import XRP1
from ixh26.contracts import AlertKind, Transfer
from ixh26.store.repo import Store

COMPROMISED_KINDS = {AlertKind.SECURITY_CHANGE.value, AlertKind.TAINT_AT_EXCHANGE.value}


@dataclass(frozen=True)
class WalletState:
    state: str  # safe | attention | compromised
    headline: str
    detail: str


def wallet_state(store: Store, user_id: int, address: str, flagged: dict[str, Any]) -> WalletState:
    unread = [a for a in store.alerts(user_id, unread_only=True) if a.wallet == address]
    if any(a.kind in COMPROMISED_KINDS for a in unread):
        return WalletState(
            "compromised",
            "Possible compromise",
            "Signing keys changed or funds were traced to an exchange. Review the notifications.",
        )
    if address in flagged:
        flag = flagged[address]
        return WalletState(
            "attention", "Flagged by an analyst", f"Category {flag.category}: {flag.reason}"
        )
    if any(a.kind == AlertKind.FLAGGED_COUNTERPARTY.value for a in unread):
        return WalletState(
            "attention",
            "Contact with a flagged account",
            "This wallet sent to or received from an account flagged by an analyst.",
        )
    return WalletState("safe", "All clear", "No unread warnings for this wallet.")


@dataclass
class AssetStatement:
    asset: str
    received: Decimal = Decimal(0)
    sent: Decimal = Decimal(0)
    count: int = 0

    @property
    def net(self) -> Decimal:
        return self.received - self.sent


def statement(address: str, transfers: list[Transfer]) -> dict[str, Any]:
    per_asset: dict[str, AssetStatement] = {}
    counterparties: set[str] = set()
    for t in transfers:
        is_xrp = t.amount.asset.is_xrp
        key = "XRP" if is_xrp else f"{t.amount.asset.currency}"
        row = per_asset.setdefault(key, AssetStatement(key))
        value = t.amount.value / XRP1 if is_xrp else t.amount.value
        if t.destination == address:
            row.received += value
            counterparties.add(t.source)
        if t.source == address:
            row.sent += value
            counterparties.add(t.destination)
        row.count += 1
    return {
        "assets": list(per_asset.values()),
        "counterparties": len(counterparties - {address}),
        "first": transfers[0].close_time if transfers else None,
        "last": transfers[-1].close_time if transfers else None,
    }


def number_in(text: str) -> Decimal:
    """'95.5 XRP' -> Decimal('95.5') (trace results store display strings)."""
    try:
        return Decimal(text.split()[0].replace(",", ""))
    except (InvalidOperation, IndexError):
        return Decimal(0)


def ribbon(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Columns by hop: who held how much of the stolen value, as a share of the theft."""
    stolen = number_in(result["params"]["stolen"]) or Decimal(1)
    unit = result["params"]["stolen"].split()[-1]
    sinks = {(s["address"], s["destination_tag"]): s for s in result["sinks"]}
    forwarded = {e["source"] for e in result["edges"]}
    # red = funds stopped here or reached a known entity; residual reserves on hops don't count
    stopped = {s["address"] for s in result["sinks"] if s["label"] or s["address"] not in forwarded}
    columns: dict[int, dict[tuple[str, int | None], Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    for e in result["edges"]:
        tag = e["destination_tag"] if (e["destination"], e["destination_tag"]) in sinks else None
        columns[e["hop"]][(e["destination"], tag)] += number_in(e["taint"])
    out = [
        {
            "hop": 0,
            "nodes": [
                {
                    "address": result["params"]["origin"],
                    "tag": None,
                    "kind": "origin",
                    "value": f"{stolen.normalize():f} {unit}",
                    "share": 100,
                    "label": "Victim",
                }
            ],
        }
    ]
    for hop in sorted(columns):
        nodes = []
        for (address, tag), value in sorted(columns[hop].items(), key=lambda kv: -kv[1]):
            sink = sinks.get((address, tag))
            nodes.append(
                {
                    "address": address,
                    "tag": tag,
                    "kind": "sink" if address in stopped else "hop",
                    "value": f"{value.quantize(Decimal('0.000001')).normalize():f} {unit}",
                    "share": float(min(value / stolen * 100, Decimal(100))),
                    "label": sink["label"] if sink and sink["label"] else None,
                }
            )
        out.append({"hop": hop, "nodes": nodes})
    return out
