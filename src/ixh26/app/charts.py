"""Server-rendered SVG charts. Pure functions: data in, markup out. No JavaScript.

- ``line_chart``: one series over time (a wallet's balance from recorded transfers).
- ``flow_graph``: where stolen funds went, hop by hop, band width = tainted value.
- ``ranked_bars``: a short ranked list with thin bars (e.g. findings per detector).

Colours come from CSS classes (``app.css``), so charts follow the design tokens.
"""

from __future__ import annotations

import zlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from html import escape
from typing import Any

from markupsafe import Markup


@dataclass(frozen=True)
class Point:
    when: datetime
    value: Decimal


def _scale(value: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    """Map ``value`` from [lo, hi] onto [out_lo, out_hi]; a flat range maps to the middle."""
    if hi == lo:
        return (out_lo + out_hi) / 2
    return out_lo + (value - lo) / (hi - lo) * (out_hi - out_lo)


def _fmt(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')).normalize():,f}"


def line_chart(points: list[Point], *, unit: str, width: int = 720, height: int = 240) -> Markup:
    """A step line with a soft area under it, min/max gridlines and a hover title per point."""
    if len(points) < 2:
        return Markup("")
    pad_l, pad_r, pad_t, pad_b = 56, 16, 16, 28
    xs = [p.when.timestamp() for p in points]
    ys = [float(p.value) for p in points]
    lo, hi = min(0.0, min(ys)), max(ys)

    def x(i: int) -> float:
        return _scale(xs[i], xs[0], xs[-1], pad_l, width - pad_r)

    def y(v: float) -> float:
        return _scale(v, lo, hi, height - pad_b, pad_t)

    # step path: balance holds until the next transfer
    path = f"M{x(0):.1f},{y(ys[0]):.1f}"
    for i in range(1, len(points)):
        path += f" H{x(i):.1f} V{y(ys[i]):.1f}"
    area = f"{path} V{y(lo):.1f} H{x(0):.1f} Z"
    grid = "".join(
        f'<line class="chart-grid" x1="{pad_l}" x2="{width - pad_r}" y1="{y(v):.1f}" '
        f'y2="{y(v):.1f}"/><text class="chart-label" x="{pad_l - 8}" y="{y(v) + 4:.1f}" '
        f'text-anchor="end">{_fmt(Decimal(str(v)))}</text>'
        for v in sorted({lo, hi})
    )
    dots = "".join(
        f'<circle class="chart-dot" cx="{x(i):.1f}" cy="{y(ys[i]):.1f}" r="4"><title>'
        f"{p.when:%d %b %H:%M} UTC: {_fmt(p.value)} {escape(unit)}</title></circle>"
        for i, p in enumerate(points)
    )
    axis = (
        f'<text class="chart-label" x="{pad_l}" y="{height - 8}">{points[0].when:%d %b %H:%M}'
        f'</text><text class="chart-label" x="{width - pad_r}" y="{height - 8}" '
        f'text-anchor="end">{points[-1].when:%d %b %H:%M}</text>'
    )
    return Markup(
        f'<svg class="chart chart-line" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Balance over time, from {_fmt(points[0].value)} to '
        f'{_fmt(points[-1].value)} {escape(unit)}">{grid}'
        f'<path class="chart-area" d="{area}"/><path class="chart-stroke" pathLength="1" '
        f'd="{path}"/>{dots}{axis}</svg>'
    )


# --- funds-flow graph ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlowNode:
    key: tuple[str, int | None]
    hop: int
    value: Decimal
    label: str
    kind: str  # origin | hop | sink


def flow_nodes(report: dict[str, Any]) -> list[FlowNode]:
    """One node per (account, tag) and hop, sized by the tainted value it received."""
    stolen = Decimal(report["params"]["stolen_value"])
    sinks = {(s["address"], s["destination_tag"]): s for s in report["sinks"]}
    forwarded = {e["source"] for e in report["edges"]}
    received: dict[tuple[tuple[str, int | None], int], Decimal] = defaultdict(Decimal)
    for e in report["edges"]:
        key = (e["destination"], e["destination_tag"])
        received[(key if key in sinks else (e["destination"], None), e["hop"])] += Decimal(
            e["taint_value"]
        )
    origin = report["params"]["origin"]
    nodes = [FlowNode((origin, None), 0, stolen, "Victim", "origin")]
    for (key, hop), value in sorted(received.items(), key=lambda kv: (kv[0][1], -kv[1])):
        sink = sinks.get(key)
        labelled = bool(sink and sink["label"])
        stopped = labelled or key[0] not in forwarded
        name = sink["label"] if labelled else f"{key[0][:6]}…{key[0][-4:]}"
        nodes.append(FlowNode(key, hop, value, name, "sink" if stopped else "hop"))
    return nodes


def flow_graph(report: dict[str, Any], *, width: int = 960, height: int = 340) -> Markup:
    """Node-link graph: one circle per account and hop, one curved arrow per tainted transfer.

    Circle size and line width follow the stolen value carried. Hops appear one after the
    other, then value particles keep flowing along the links (SVG animation, no JavaScript).
    """
    nodes = flow_nodes(report)
    if len(nodes) < 2:
        return Markup("")
    stolen = Decimal(report["params"]["stolen_value"])
    unit = report["params"]["stolen"].split()[-1]
    per_unit = Decimal(10**6) if unit == "XRP" else Decimal(1)
    hops = max(n.hop for n in nodes)
    uid = zlib.crc32(f"{report['params']['origin']}{report.get('computed_at')}".encode()) % 10**6
    pad_y = 48

    def radius(value: Decimal) -> float:
        return 9 + 17 * float(min(value / stolen, Decimal(1)))

    pos: dict[tuple[tuple[str, int | None], int], tuple[float, float, float]] = {}
    for hop in range(hops + 1):
        column = [n for n in nodes if n.hop == hop]
        x = _scale(hop, 0, hops, 90, width - 210)
        for row, n in enumerate(column):
            y = _scale(row + 0.5, 0, len(column), pad_y, height - 24)
            pos[(n.key, n.hop)] = (x, y, radius(n.value))

    links, particles = [], []
    for e in report["edges"]:
        src = next((k for k in pos if k[0][0] == e["source"] and k[1] == e["hop"] - 1), None)
        dst = next((k for k in pos if k[0][0] == e["destination"] and k[1] == e["hop"]), None)
        if src is None or dst is None:
            continue
        (sx, sy, sr), (dx, dy, dr) = pos[src], pos[dst]
        x0, x1 = sx + sr + 2, dx - dr - 6
        mid = (x0 + x1) / 2
        d = f"M{x0:.1f},{sy:.1f} C{mid:.1f},{sy:.1f} {mid:.1f},{dy:.1f} {x1:.1f},{dy:.1f}"
        share = float(Decimal(e["taint_value"]) / stolen)
        link_id = f"link-{uid}-{len(links)}"
        links.append(
            f'<path id="{link_id}" class="flow-band" style="--i:{e["hop"]}" pathLength="1" '
            f'stroke-width="{1.5 + 4.5 * share:.1f}" marker-end="url(#arrow-{uid})" d="{d}">'
            f"<title>{escape(e['taint'])} via {escape(e['tx_hash'][:12])}…</title></path>"
        )
        for k in range(1 + round(share * 2)):  # bigger flows carry more particles
            begin = 0.45 * e["hop"] + 1.0 + k * 0.7
            particles.append(
                f'<circle class="flow-particle" opacity="0" r="{2.5 + 2 * share:.1f}">'
                f'<set attributeName="opacity" to="1" begin="{begin:.2f}s"/>'
                f'<animateMotion dur="1.4s" begin="{begin:.2f}s" repeatCount="indefinite">'
                f'<mpath href="#{link_id}"/></animateMotion></circle>'
            )

    circles = []
    for n in nodes:
        x, y, r = pos[(n.key, n.hop)]
        tag = f", tag {n.key[1]}" if n.key[1] is not None else ""
        value = f"{(n.value / per_unit).quantize(Decimal('0.000001')).normalize():,f} {unit}"
        share = n.value / stolen * 100
        ring = (
            f'<circle class="flow-ring" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'
            if n.kind == "sink"
            else ""
        )
        circles.append(
            f'<g class="flow-node flow-{n.kind}" style="--i:{n.hop}">{ring}'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"><title>{escape(n.key[0])}'
            f"{escape(tag)}: {value}</title></circle>"
            f'<text class="flow-name" x="{x:.1f}" y="{y + r + 15:.1f}" text-anchor="middle">'
            f"{escape(n.label)}{escape(tag)}</text>"
            f'<text class="flow-value" x="{x:.1f}" y="{y + r + 29:.1f}" text-anchor="middle">'
            f"{value} ({share:.0f}%)</text></g>"
        )
    hop_labels = "".join(
        f'<text class="chart-label" x="{_scale(h, 0, hops, 90, width - 210):.1f}" y="18" '
        f'text-anchor="middle">{"Victim" if h == 0 else f"Hop {h}"}</text>'
        for h in range(hops + 1)
    )
    arrow = (
        f'<defs><marker id="arrow-{uid}" viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" markerWidth="11" '
        'markerHeight="11" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'class="flow-arrow"/></marker></defs>'
    )
    return Markup(
        f'<svg class="chart flow" viewBox="0 0 {width} {height + 30}" role="img" '
        f'aria-label="Funds flow over {hops} hops">{arrow}{hop_labels}{"".join(links)}'
        f'<g class="flow-particles">{"".join(particles)}</g>{"".join(circles)}</svg>'
    )


def ranked_bars(items: list[tuple[str, int]]) -> list[dict[str, Any]]:
    """[(label, count)] -> rows with a bar width in %, largest first."""
    top = max((c for _, c in items), default=0) or 1
    return [
        {"label": label, "count": count, "pct": round(count / top * 100)}
        for label, count in sorted(items, key=lambda kv: -kv[1])
    ]
