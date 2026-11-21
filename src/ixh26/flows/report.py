"""Incident report: what happened to one wallet, built from stored ledger data.

``build_incident`` gathers the facts once; the recovery page shows them and ``incident_pdf``
prints them for an exchange or the police. Every fact links to a validated transaction.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fpdf import FPDF

from ixh26 import config
from ixh26.contracts import SecurityEvent, Transfer
from ixh26.core.alerts import amount_text
from ixh26.store.models import TraceRow
from ixh26.store.repo import Store, traces_of

BRAND = "Ripple Guardian"


@dataclass(frozen=True)
class Step:
    """One line of the incident timeline."""

    when: datetime
    title: str
    detail: str
    tx_hash: str
    kind: str  # key | out | in


@dataclass(frozen=True)
class Incident:
    wallet: str
    label: str
    network: str
    generated_at: datetime
    timeline: tuple[Step, ...]
    stolen_drops: Decimal  # XRP sent after the first key change (0 if no key change)
    sinks: tuple[dict[str, Any], ...] = ()  # from the latest finished trace
    trace_id: int | None = None
    trace_pending: bool = False
    first_theft_ledger: int | None = None
    tx_hashes: tuple[str, ...] = field(default=())

    @property
    def compromised(self) -> bool:
        return any(s.kind == "key" for s in self.timeline)

    @property
    def fingerprint(self) -> str:
        """SHA-256 over the sorted evidence hashes: lets anyone check the list is complete."""
        return hashlib.sha256("\n".join(sorted(self.tx_hashes)).encode()).hexdigest()

    @property
    def reference(self) -> str:
        return f"RG-{self.fingerprint[:10].upper()}"

    @property
    def exchanges(self) -> list[dict[str, Any]]:
        return [s for s in self.sinks if s.get("label")]


def _key_step(e: SecurityEvent) -> Step:
    titles = {
        "set_regular_key": "Signing key changed",
        "signer_list_set": "Signer list changed",
        "master_key_disabled": "Master key disabled",
        "account_delete": "Account deleted",
    }
    detail = f"new key {e.detail}" if e.detail and e.detail != "removed" else e.detail
    return Step(e.close_time, titles.get(e.kind.value, e.kind.value), detail, e.tx_hash, "key")


def _transfer_step(t: Transfer, wallet: str) -> Step:
    if t.source == wallet:
        tag = f", tag {t.destination_tag}" if t.destination_tag is not None else ""
        return Step(
            t.close_time,
            f"Sent {amount_text(t.amount)}",
            f"to {t.destination}{tag}",
            t.tx_hash,
            "out",
        )
    return Step(
        t.close_time, f"Received {amount_text(t.amount)}", f"from {t.source}", t.tx_hash, "in"
    )


def _latest_trace(store: Store, wallet: str) -> tuple[TraceRow | None, bool]:
    rows = traces_of(store, wallet)
    done = next((r for r in rows if r.status == "done" and r.result), None)
    return done, any(r.status == "pending" for r in rows)


def build_incident(store: Store, user_id: int, wallet: str, settings: config.Settings) -> Incident:
    """Facts about ``wallet`` since its last key change (or its whole history if none)."""
    row = store.wallet(user_id, wallet)
    if row is None:
        raise LookupError("not one of your wallets")
    events = store.events_of([wallet])
    since = max(((e.ledger_index, e.tx_index) for e in events), default=None)
    transfers = [
        t
        for t in store.transfers_of([wallet])
        if since is None or (t.ledger_index, t.tx_index) >= since
    ]
    if since is not None:
        events = [e for e in events if (e.ledger_index, e.tx_index) == since]
    steps = sorted(
        [_key_step(e) for e in events] + [_transfer_step(t, wallet) for t in transfers],
        key=lambda s: s.when,
    )
    stolen = sum(
        (t.amount.value for t in transfers if t.source == wallet and t.amount.asset.is_xrp),
        Decimal(0),
    )
    first_out = next((t for t in transfers if t.source == wallet), None)
    trace, pending = _latest_trace(store, wallet)
    sinks = tuple(trace.result["sinks"]) if trace else ()
    edges = trace.result["edges"] if trace else []
    hashes = {s.tx_hash for s in steps} | {e["tx_hash"] for e in edges}
    return Incident(
        wallet=wallet,
        label=row.label or "Unnamed wallet",
        network=settings.network.name,
        generated_at=datetime.now(UTC),
        timeline=tuple(steps),
        stolen_drops=stolen if since is not None else Decimal(0),
        sinks=sinks,
        trace_id=trace.id if trace else None,
        trace_pending=pending,
        first_theft_ledger=first_out.ledger_index if first_out and since else None,
        tx_hashes=tuple(sorted(hashes)),
    )


# --- PDF ---------------------------------------------------------------------------------------

INK = (17, 24, 39)
MUTED = (107, 116, 135)
ACCENT = (10, 100, 214)
DANGER = (197, 40, 61)


def _latin1(text: str) -> str:
    """Core PDF fonts are Latin-1: replace the few characters our copy uses outside it."""
    return (
        text.replace("…", "...")
        .replace("\u2212", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class _Report(FPDF):
    def header(self) -> None:
        self.set_fill_color(*INK)
        self.rect(0, 0, 210, 22, "F")
        self.set_draw_color(94, 162, 245)
        self.set_line_width(0.6)
        for r in (3, 5.5, 8):  # the ripple mark
            self.circle(18, 11, r, style="D")
        self.set_xy(30, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, BRAND)
        self.set_xy(30, 12)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(170, 185, 210)
        self.cell(0, 5, "Incident report for a compromised XRP Ledger wallet")
        self.set_y(30)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            5,
            _latin1(
                f"{BRAND} | heuristic attribution, verify each transaction | page {self.page_no()}"
            ),
            align="C",
        )

    def section(self, title: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*INK)
        self.cell(0, 7, _latin1(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 224, 232)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(2)

    def pair(self, key: str, value: str, mono: bool = False) -> None:
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.cell(42, 5.5, _latin1(key))
        self.set_text_color(*INK)
        self.set_font("Courier" if mono else "Helvetica", "", 8.5 if mono else 9.5)
        self.multi_cell(0, 5.5, _latin1(value), new_x="LMARGIN", new_y="NEXT")


def _xrp(drops: Decimal | str) -> str:
    return (
        f"{(Decimal(drops) / Decimal(1_000_000)).quantize(Decimal('0.000001')).normalize():f} XRP"
    )


def incident_pdf(incident: Incident, settings: config.Settings) -> bytes:
    tx_url = settings.network.explorer_tx_url
    pdf = _Report(format="A4")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*(DANGER if incident.compromised else INK))
    headline = "Wallet compromised" if incident.compromised else "Wallet activity report"
    pdf.cell(0, 10, headline, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.pair("Reference", incident.reference, mono=True)
    pdf.pair("Wallet", f"{incident.label}  {incident.wallet}")
    pdf.pair("Network", f"XRP Ledger {incident.network.capitalize()}")
    pdf.pair("Generated", incident.generated_at.strftime("%d %b %Y, %H:%M UTC"))
    if incident.compromised:
        pdf.pair("Stolen", _xrp(incident.stolen_drops))
    for ex in incident.exchanges:
        tag = ex["destination_tag"]
        pdf.pair(
            "Received by",
            f"{ex['label']}  {ex['address']}" + (f"  tag {tag}" if tag is not None else ""),
        )
        pdf.pair("Amount traced", f"{ex['taint']} ({float(ex['share']) * 100:.1f}% of the theft)")

    pdf.section("What happened")
    for step in incident.timeline:
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(30, 5, step.when.strftime("%d %b %H:%M:%S"))
        pdf.set_text_color(*(DANGER if step.kind == "key" else INK))
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(48, 5, _latin1(step.title))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, 5, _latin1(step.detail), new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(46)
        pdf.set_font("Courier", "", 7)
        pdf.set_text_color(*ACCENT)
        pdf.cell(
            0, 4, step.tx_hash, link=tx_url.format(hash=step.tx_hash), new_x="LMARGIN", new_y="NEXT"
        )
        pdf.ln(1)

    if incident.sinks:
        pdf.section("Where the funds went (haircut taint trace)")
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*MUTED)
        for head, width in (("Account", 92), ("Known as", 40), ("Amount", 30), ("Share", 16)):
            pdf.cell(width, 5, head)
        pdf.ln(6)
        for s in incident.sinks:
            tag = f" tag {s['destination_tag']}" if s["destination_tag"] is not None else ""
            pdf.set_font("Courier", "", 7.5)
            pdf.set_text_color(*INK)
            pdf.cell(92, 5, f"{s['address']}{tag}")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.cell(40, 5, _latin1(s["label"] or "unlabelled"))
            pdf.cell(30, 5, s["taint"])
            pdf.cell(16, 5, f"{float(s['share']) * 100:.1f}%", new_x="LMARGIN", new_y="NEXT")

    if incident.exchanges:
        pdf.section("Request to the exchange")
        ex = incident.exchanges[0]
        tag = ex["destination_tag"]
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(
            0,
            5.5,
            _latin1(
                f"Funds stolen from wallet {incident.wallet} reached your deposit address "
                f"{ex['address']}"
                + (f" with destination tag {tag}" if tag is not None else "")
                + f". We traced {ex['taint']} to that deposit. Please freeze the customer account"
                " behind it and preserve its records while the police investigate."
                f" Our reference: {incident.reference}."
            ),
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.section("Evidence")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        0,
        4.5,
        _latin1(
            "Each transaction below is validated on the XRP Ledger and can be checked in any "
            "explorer. The SHA-256 fingerprint covers the sorted list of hashes."
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    pdf.set_font("Courier", "", 7)
    for h in incident.tx_hashes:
        pdf.set_text_color(*ACCENT)
        pdf.cell(
            0, 4, tx_url.format(hash=h), link=tx_url.format(hash=h), new_x="LMARGIN", new_y="NEXT"
        )
    pdf.ln(2)
    pdf.set_text_color(*INK)
    pdf.pair("SHA-256", incident.fingerprint, mono=True)
    return bytes(pdf.output())
