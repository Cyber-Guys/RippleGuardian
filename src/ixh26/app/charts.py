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


def flow_graph(report: dict[str, Any], *, width: int = 960, height: int = 320) -> Markup:
    """Columns by hop; each band is one tainted transfer, as thick as the value it carried."""
    nodes = flow_nodes(report)
    if len(nodes) < 2:
        return Markup("")
    stolen = Decimal(report["params"]["stolen_value"])
    unit = report["params"]["stolen"].split()[-1]
    per_unit = Decimal(10**6) if unit == "XRP" else Decimal(1)
    hops = max(n.hop for n in nodes)
    col_w, gap, pad = 14, 10, 28
    usable = height - 2 * pad
    scale = Decimal(usable) * Decimal("0.85") / stolen

    def col_x(hop: int) -> float:
        return _scale(hop, 0, hops, 170, width - 300)

    pos: dict[tuple[tuple[str, int | None], int], tuple[float, float, float]] = {}
    for hop in range(hops + 1):
        column = [n for n in nodes if n.hop == hop]
        total = sum(float(n.value * scale) for n in column) + gap * (len(column) - 1)
        top = pad + (usable - total) / 2
        for n in column:
            h = max(float(n.value * scale), 3.0)
            pos[(n.key, n.hop)] = (col_x(hop), top, h)
            top += h + gap

    out_used: dict[tuple, float] = defaultdict(float)
    in_used: dict[tuple, float] = defaultdict(float)
    bands: list[str] = []
    particles: list[str] = []
    uid = zlib.crc32(f"{report['params']['origin']}{report.get('computed_at')}".encode()) % 10**6
    for e in sorted(report["edges"], key=lambda e: (e["hop"], -Decimal(e["taint_value"]))):
        src_key = next((k for k in pos if k[0][0] == e["source"] and k[1] == e["hop"] - 1), None)
        dst_key = next((k for k in pos if k[0][0] == e["destination"] and k[1] == e["hop"]), None)
        if src_key is None or dst_key is None:
            continue
        thick = max(float(Decimal(e["taint_value"]) * scale), 1.5)
        sx, sy, _ = pos[src_key]
        dx, dy, _ = pos[dst_key]
        y0 = sy + out_used[src_key] + thick / 2
        y1 = dy + in_used[dst_key] + thick / 2
        out_used[src_key] += thick
        in_used[dst_key] += thick
        mid = (sx + col_w + dx) / 2
        d = f"M{sx + col_w:.1f},{y0:.1f} C{mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {dx:.1f},{y1:.1f}"
        band_id = f"band-{uid}-{len(bands)}"
        bands.append(
            f'<path id="{band_id}" class="flow-band" style="--i:{e["hop"]}" pathLength="1" '
            f'stroke-width="{thick:.1f}" d="{d}"><title>{escape(e["taint"])} via '
            f"{escape(e['tx_hash'][:12])}…</title></path>"
        )
        # value "particles": bigger flows carry more dots; they start once their hop has drawn
        dots = 1 + min(int(thick // 14), 3)
        for k in range(dots):
            begin = 0.35 * e["hop"] + 1.2 + k * 1.6 / dots
            particles.append(
                f'<circle class="flow-particle" opacity="0" r="{min(2 + thick / 18, 4.5):.1f}">'
                f'<set attributeName="opacity" to="1" begin="{begin:.2f}s"/>'
                f'<animateMotion dur="1.6s" begin="{begin:.2f}s" repeatCount="indefinite">'
                f'<mpath href="#{band_id}"/></animateMotion></circle>'
            )
    rects = []
    for n in nodes:
        x, top, h = pos[(n.key, n.hop)]
        share = n.value / stolen * 100
        value = f"{(n.value / per_unit).quantize(Decimal('0.000001')).normalize():,f} {unit}"
        anchor, tx = ("end", x - 8) if n.hop == 0 else ("start", x + col_w + 8)
        tag = f", tag {n.key[1]}" if n.key[1] is not None else ""
        rects.append(
            f'<g class="flow-node flow-{n.kind}" style="--i:{n.hop}"><rect x="{x:.1f}" '
            f'y="{top:.1f}" width="{col_w}" height="{h:.1f}" rx="4"><title>{escape(n.key[0])}'
            f"{escape(tag)}: {value}</title></rect>"
            f'<text class="flow-name" x="{tx:.1f}" y="{top + h / 2 - 2:.1f}" '
            f'text-anchor="{anchor}">{escape(n.label)}{escape(tag)}</text>'
            f'<text class="flow-value" x="{tx:.1f}" y="{top + h / 2 + 13:.1f}" '
            f'text-anchor="{anchor}">{value} ({share:.0f}%)</text></g>'
        )
    hop_labels = "".join(
        f'<text class="chart-label" x="{col_x(h) + col_w / 2:.1f}" y="14" text-anchor="middle">'
        f"{'Victim' if h == 0 else f'Hop {h}'}</text>"
        for h in range(hops + 1)
    )
    return Markup(
        f'<svg class="chart flow" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Funds flow over {hops} hops">{hop_labels}{"".join(bands)}'
        f'<g class="flow-particles">{"".join(particles)}</g>{"".join(rects)}</svg>'
    )


def ranked_bars(items: list[tuple[str, int]]) -> list[dict[str, Any]]:
    """[(label, count)] -> rows with a bar width in %, largest first."""
    top = max((c for _, c in items), default=0) or 1
    return [
        {"label": label, "count": count, "pct": round(count / top * 100)}
        for label, count in sorted(items, key=lambda kv: -kv[1])
    ]
