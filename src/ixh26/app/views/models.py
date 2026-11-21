"""View models: turn stored rows into what a page shows. No HTTP here."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ixh26.app.charts import Point, ranked_bars
from ixh26.app.views.common import XRP1
from ixh26.contracts import AlertKind, Transfer
from ixh26.store.repo import Store

COMPROMISED_KINDS = {AlertKind.SECURITY_CHANGE.value, AlertKind.TAINT_AT_EXCHANGE.value}


@dataclass(frozen=True)
class WalletState:
    """What a wallet owner needs to know first: how worried to be, and what to do now."""

    state: str  # safe | attention | compromised
    headline: str
    detail: str
    steps: tuple[str, ...] = ()

    @property
    def icon(self) -> str:
        return {"safe": "shield-check", "attention": "triangle-alert"}.get(
            self.state, "shield-alert"
        )


COMPROMISED_STEPS = (
    "Stop using this wallet's secret key: whoever changed the keys can sign for it.",
    "Move anything left to a brand-new wallet created on a device you trust.",
    "Open the notifications: they show where the funds went and under which exchange tag.",
    "Report it to that exchange and to the police, with the transaction links.",
)


def wallet_state(store: Store, user_id: int, address: str, flagged: dict[str, Any]) -> WalletState:
    """Worst first: a compromise beats an analyst flag, which beats a risky contact."""
    unread = [a for a in store.alerts(user_id, unread_only=True) if a.wallet == address]
    if any(a.kind in COMPROMISED_KINDS for a in unread):
        return WalletState(
            "compromised",
            "This wallet may be compromised",
            "Its keys changed and funds left. Act now.",
            COMPROMISED_STEPS,
        )
    if address in flagged:
        flag = flagged[address]
        return WalletState(
            "attention",
            "An analyst flagged this wallet",
            f"Category {flag.category}: {flag.reason}",
        )
    if any(a.kind == AlertKind.FLAGGED_COUNTERPARTY.value for a in unread):
        return WalletState(
            "attention",
            "This wallet touched a flagged account",
            "Don't send it more funds until you check.",
        )
    return WalletState("safe", "All clear", "Nothing unusual.")


def overall_state(named: list[tuple[str, WalletState]]) -> WalletState:
    """The dashboard headline: the most serious state among the user's wallets, by name."""
    order = {"compromised": 0, "attention": 1, "safe": 2}
    if not named:
        return WalletState("safe", "No wallets yet", "Add one to start watching it.")
    name, worst = min(named, key=lambda ns: order[ns[1].state])
    if worst.state == "safe":
        return WalletState("safe", "All wallets safe", "We're watching the ledger for you.")
    headline = worst.headline.replace("This wallet", name, 1)
    return WalletState(worst.state, headline, worst.detail, worst.steps)


def balance_points(address: str, transfers: list[Transfer]) -> list[Point]:
    """XRP balance after each recorded transfer (fees and reserves not included)."""
    points, running = [], Decimal(0)
    for t in transfers:
        if not t.amount.asset.is_xrp:
            continue
        if t.destination == address:
            running += t.amount.value / XRP1
        if t.source == address:
            running -= (t.source_amount or t.amount).value / XRP1
        points.append(Point(t.close_time, running))
    return points


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


def analyst_overview(store: Store) -> dict[str, Any]:
    """Counts and lists for the analyst dashboard, all from stored data."""
    findings = store.findings()
    traces = store.traces()
    by_kind: dict[str, int] = defaultdict(int)
    for f in findings:
        by_kind[f.kind.replace("_", " ").capitalize()] += 1
    latest_done = next((t for t in traces if t.status == "done" and t.result), None)
    exposure = exchange_exposure(traces)
    return {
        "xrp_located": sum((e["xrp"] for e in exposure), Decimal(0)),
        "exposure": exposure,
        "open_findings": sum(f.status == "open" for f in findings),
        "active_flags": len(store.flags()),
        "watched": len(store.watched_addresses()),
        "traces_done": sum(t.status == "done" for t in traces),
        "by_kind": ranked_bars(list(by_kind.items())),
        "recent_findings": findings[:6],
        "latest_trace": latest_done,
    }


def exchange_exposure(traces: list[Any]) -> list[dict[str, Any]]:
    """Stolen XRP that reached each known entity and deposit tag, summed over finished traces.

    This is the list an exchange acts on: which customer account (tag) to freeze.
    """
    totals: dict[tuple[str, str, int | None], Decimal] = defaultdict(Decimal)
    for row in traces:
        if row.status != "done" or not row.result or row.currency != "XRP":
            continue
        for s in row.result["sinks"]:
            if s.get("label") and "taint_value" in s:
                key = (s["label"], s["address"], s["destination_tag"])
                totals[key] += Decimal(s["taint_value"]) / XRP1
    top = max(totals.values(), default=Decimal(1)) or Decimal(1)
    return [
        {"label": k[0], "address": k[1], "tag": k[2], "xrp": v, "pct": round(v / top * 100)}
        for k, v in sorted(totals.items(), key=lambda kv: -kv[1])
    ]
