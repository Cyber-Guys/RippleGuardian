"""Capture the real Ripple Guardian screens for the trailer, in one pass.

    uv run --with playwright python docs/trailer/capture.py [--trace 1]

The app runs on another machine behind TRAILER_BASE_URL (an ngrok URL). TRAILER_USER and
TRAILER_ANALYST are name:password. All three are read from the environment and never written
anywhere. Output goes to docs/trailer/public/captures/ (git-ignored): 2x PNG screenshots,
1920x1080 WebM recordings, the server's HTML of each page (site/, for re-shooting offline)
and manifest.json with the values the app shows and the box of each key element, in CSS
pixels of the 1920x1080 viewport.

The login and page flow follow scripts/e2e_browser.py. Nothing is written to the app.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "public" / "captures"
VIEW = {"width": 1920, "height": 1080}
NGROK = {"ngrok-skip-browser-warning": "true"}  # free ngrok shows a warning page otherwise
EXPLORER = "https://testnet.xrpl.org/transactions/{}"
HOP_MS = 2000  # one hop per bar at 120 BPM; the app itself uses 450 ms
FOCUS_TAG = "777001"
# Each exchange gets its own alert: take the one for FOCUS_TAG.
LOCATED = f".x-item:has-text('Stolen funds located'):has-text('{FOCUS_TAG}')"
WINDOWS_FONTS = Path("/mnt/c/Windows/Fonts")
FONT_FILES = ("segoeui*.ttf", "segui*.ttf", "seguivar.ttf", "consola*.ttf", "cascadia*.ttf")

NEUTRAL = (VIEW["width"] - 2, VIEW["height"] - 2)  # parks the mouse where it hovers nothing

# Resolves once every finite animation and transition on the page has finished (6 s at most).
SETTLE = """() => Promise.race([
  Promise.all(document.getAnimations()
    .filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity)
    .map(a => a.finished.catch(() => null))),
  new Promise(r => setTimeout(r, 6000)),
]).then(() => true)"""

# Headless Chromium draws no pointer: this one follows the real mouse events.
CURSOR = """(() => {
  const draw = () => {
    if (document.getElementById('trailer-cursor')) return;
    const c = document.createElement('div');
    c.id = 'trailer-cursor';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 30 30"><path d="M6 3v21l5.2-4.9 '
      + '3.6 7.9 3.6-1.6-3.6-7.7H22z" fill="#0b1220" stroke="#fff" stroke-width="1.8" '
      + 'stroke-linejoin="round"/></svg><i></i>';
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;'
      + 'transform:translate(-200px,-200px);filter:drop-shadow(0 2px 4px rgb(0 0 0 / .35))';
    const ring = c.querySelector('i');
    ring.style.cssText = 'position:absolute;left:-12px;top:-15px;width:36px;height:36px;'
      + 'border-radius:50%;border:2px solid #5ea2f5;opacity:0';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => {
      c.style.transform = `translate(${e.clientX - 6}px, ${e.clientY - 3}px)`;
    }, true);
    addEventListener('mousedown', () => ring.animate(
      [{opacity: 0.9, transform: 'scale(.4)'}, {opacity: 0, transform: 'scale(1.4)'}],
      {duration: 450, easing: 'cubic-bezier(0.16, 1, 0.3, 1)'}), true);
  };
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', draw) : draw();
})()"""

# Trace recording only: hop h appears at h * HOP_MS instead of h * 450 ms. Pop, draw and
# particle speeds are the app's own; particles start once their link is drawn, as in the app.
# Arrowheads wait for their link: at 2 s per hop they would float alone for seconds.
RETIME = """(() => {
  const hop = HOP_MS;
  const run = () => {
    const s = document.createElement('style');
    s.textContent = `.flow-node{animation-delay:calc(var(--i,0) * ${hop}ms)!important}`
      + `.flow-band{animation-delay:calc(var(--i,0) * ${hop}ms + 200ms)!important}`;
    document.head.appendChild(s);
    for (const b of document.querySelectorAll('.flow-band')) {
      const marker = b.getAttribute('marker-end');
      b.removeAttribute('marker-end');
      b.addEventListener('animationend', () => b.setAttribute('marker-end', marker), {once: true});
    }
    for (const c of document.querySelectorAll('.flow-particle')) {
      const link = document.getElementById(c.querySelector('mpath').getAttribute('href').slice(1));
      const h = parseFloat(link.style.getPropertyValue('--i'));
      for (const a of c.querySelectorAll('set, animateMotion')) {
        const begin = parseFloat(a.getAttribute('begin')) + h * (hop - 450) / 1000;
        a.setAttribute('begin', begin.toFixed(2) + 's');
      }
    }
  };
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', run) : run();
})()""".replace("HOP_MS", str(HOP_MS))

# The trace graph: every node, the exchange node for FOCUS_TAG and the biggest mule feeding it.
GRAPH = """tag => {
  const nodes = [...document.querySelectorAll('.flow-node')];
  const name = n => n.querySelector('.flow-name')?.textContent ?? '';
  const hop = n => Number(n.style.getPropertyValue('--i'));
  const radius = n => n.querySelector('.flow-body').r.baseVal.value;
  const ex = nodes.find(n => name(n).endsWith('tag ' + tag));
  if (!ex) return null;
  const [, uid, idx] = ex.id.split('-');
  const mule = nodes.filter(n => hop(n) === hop(ex) - 1 && n.classList.contains(`p-${uid}-${idx}`))
    .sort((a, b) => radius(b) - radius(a))[0];
  return {
    exchange: '#' + ex.id,
    mule: mule ? '#' + mule.id : null,
    hops: Math.max(...nodes.map(hop)),
    nodes: nodes.map(n => ({id: '#' + n.id, hop: hop(n), label: n.getAttribute('aria-label'),
      kind: n.classList.contains('flow-sink') ? 'sink'
        : n.classList.contains('flow-origin') ? 'origin' : 'hop'})),
    labels: nodes.filter(n => name(n))
      .map(n => [name(n), n.querySelector('.flow-value').textContent]),
  };
}"""


def creds(var: str) -> tuple[str, str]:
    name, sep, password = os.environ.get(var, "").partition(":")
    if not (name and sep and password):
        raise SystemExit(f"{var} must be set to name:password")
    return name, password


def browser_env() -> dict[str, str]:
    """The browser's environment: no trailer secrets, plus the Windows UI fonts on WSL.

    The app asks for Segoe UI and Cascadia/Consolas. Without them headless Chromium on Linux
    falls back to DejaVu, which is not what a judge on Windows sees.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("TRAILER_")}
    if not WINDOWS_FONTS.is_dir():
        return env
    fonts = Path(tempfile.mkdtemp(prefix="trailer-fonts-"))
    for f in WINDOWS_FONTS.iterdir():
        if any(fnmatch.fnmatch(f.name.lower(), p) for p in FONT_FILES):
            shutil.copy(f, fonts / f.name)
    conf = fonts / "fonts.conf"
    conf.write_text(
        '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
        f'<include ignore_missing="yes">/etc/fonts/fonts.conf</include><dir>{fonts}</dir>'
        "</fontconfig>"
    )
    return env | {"FONTCONFIG_FILE": str(conf)}


def path_of(page: Page) -> str:
    parts = urlsplit(page.url)  # never print the host: it is the ngrok URL
    return parts.path + (f"?{parts.query}" if parts.query else "")


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate(SETTLE)
    page.wait_for_timeout(300)


def visit(page: Page, url: str) -> None:
    response = page.goto(url)
    if response is None or response.status != 200:
        status = response.status if response else "no response"
        raise SystemExit(f"{path_of(page)}: HTTP {status}")
    settle(page)


def box(page: Page, selector: str) -> dict[str, float]:
    found = page.locator(selector).first.bounding_box()
    if found is None:
        raise SystemExit(f"{path_of(page)}: {selector} is not visible")
    scroll = page.evaluate("scrollY")
    return {
        "x": round(found["x"], 1),
        "y": round(found["y"] + scroll, 1),
        "w": round(found["width"], 1),
        "h": round(found["height"], 1),
    }


def center(page: Page, selector: str) -> tuple[float, float]:
    b = box(page, selector)
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


def text(page: Page, selector: str) -> str:
    return " ".join(page.locator(selector).first.inner_text().split())


def glide(page: Page, start: tuple[float, float], end: tuple[float, float], ms: int) -> None:
    """Move the mouse on a slight arc with ease-in-out, taking `ms` of wall time."""
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    began = time.monotonic()
    while True:
        t = min(1.0, (time.monotonic() - began) * 1000 / ms)
        e = 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
        arc = math.sin(math.pi * e) * 0.05 * length
        page.mouse.move(x0 + (x1 - x0) * e + nx * arc, y0 + (y1 - y0) * e + ny * arc)
        if t >= 1.0:
            return
        page.wait_for_timeout(8)


class Capture:
    def __init__(self, base: str, browser: Browser) -> None:
        self.base = base
        self.browser = browser
        self.manifest: dict[str, Any] = {
            "viewport": {**VIEW, "deviceScaleFactor": 2},
            "values": {},
            "captures": [],
        }

    def context(self, state: Any = None, video: bool = False) -> BrowserContext:
        ctx = self.browser.new_context(
            viewport=VIEW,
            device_scale_factor=2,
            extra_http_headers=NGROK,
            storage_state=state,
            record_video_dir=str(OUT / "_video") if video else None,
            record_video_size=VIEW if video else None,
        )
        ctx.add_init_script(CURSOR)
        return ctx

    def url(self, path: str) -> str:
        return f"{self.base}{path}"

    def login(self, ctx: BrowserContext, who: tuple[str, str]) -> Page:
        page = ctx.new_page()
        page.goto(self.url("/login"))
        page.fill("#username", who[0])
        page.fill("#password", who[1])
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        if page.locator(".signout span").count() == 0 or text(page, ".signout span") != who[0]:
            raise SystemExit(f"login failed for {who[0]} (now on {path_of(page)})")
        print(f"ok  signed in as {who[0]}")
        return page

    def shoot(
        self, page: Page, name: str, boxes: dict[str, str], full: bool = False, cursor: bool = False
    ) -> None:
        file = f"{name}.png"
        page.evaluate(
            "v => { const c = document.getElementById('trailer-cursor');"
            " if (c) c.style.visibility = v ? 'visible' : 'hidden'; }",
            cursor,
        )
        page.screenshot(path=OUT / file, full_page=full)
        size = page.evaluate("[innerWidth, document.documentElement.scrollHeight]")
        self.keep_html(page)
        self.manifest["captures"].append(
            {
                "file": file,
                "kind": "screenshot",
                "page": path_of(page),
                "size": {"width": VIEW["width"], "height": size[1] if full else VIEW["height"]},
                "scale": 2,
                "boxes": {key: box(page, sel) for key, sel in boxes.items()},
            }
        )
        print(f"ok  {path_of(page):<44} -> {file}")

    def keep_html(self, page: Page) -> None:
        """Save the server's HTML of this page, to re-shoot it offline once the tunnel is gone.

        Saved as site/<path>/index.html, so `python -m http.server -d site` serves it again.
        """
        dest = OUT / "site" / urlsplit(page.url).path.strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page.context.request.get(page.url).text())

    def keep_static(self, ctx: BrowserContext) -> None:
        for name in ("app.css", "htmx.min.js", "logo-mark.png", "logo.png"):
            response = ctx.request.get(self.url(f"/static/{name}"))
            if not response.ok:
                raise SystemExit(f"/static/{name}: HTTP {response.status}")
            (OUT / "site" / "static").mkdir(parents=True, exist_ok=True)
            (OUT / "site" / "static" / name).write_bytes(response.body())

    def record(self, name: str, page: Page, started: float, marks: dict, boxes: dict) -> None:
        video = page.video
        page.close()
        if video is None:
            raise SystemExit(f"{name}: no video recorded")
        file = f"{name}.webm"
        video.save_as(OUT / file)
        page.context.close()
        self.manifest["captures"].append(
            {
                "file": file,
                "kind": "video",
                "fps": 25,
                "size": VIEW,
                "marks": {k: round(v - started, 3) for k, v in marks.items()},
                "boxes": boxes,
            }
        )
        print(f"ok  recording -> {file}  marks {self.manifest['captures'][-1]['marks']}")

    # ----- owner -----------------------------------------------------------------------

    def owner(self, who: tuple[str, str]) -> Any:
        ctx = self.context()
        page = self.login(ctx, who)
        values = self.manifest["values"]

        visit(page, self.url("/"))
        card = page.locator("a.wallet-card[data-state=compromised]")
        if card.count() == 0:
            raise SystemExit("alice has no compromised wallet: run make demo on the app machine")
        wallet = (card.first.get_attribute("href") or "").split("/")[2]
        values["wallet"] = wallet
        values["alarm"] = [text(page, ".alarm h2"), text(page, ".alarm p")]
        values["kpis"] = page.locator(".kpi").all_inner_texts()
        values["feed"] = page.locator(".x-item .x-head strong").all_inner_texts()
        feed = "section.panel:has(.xlist)"
        self.shoot(
            page,
            "owner-dashboard",
            {
                "status": ".alarm",
                "whatToDo": ".alarm a.btn-danger",
                "report": ".alarm a.btn-quiet",
                "kpis": ".kpis",
                "feed": feed,
                "alertKey": f"{feed} .x-item:has-text('Signing key changed')",
                "alertSent": f"{feed} .x-item:has-text('XRP sent')",
                "wallets": "a.wallet-card",
            },
        )
        page.click("details.disclose > summary")
        settle(page)
        self.shoot(
            page,
            "owner-watch",
            {"form": "details.disclose", "watch": "details.disclose form", "card": "a.wallet-card"},
        )

        visit(page, self.url(f"/wallets/{wallet}"))
        self.shoot(
            page,
            "owner-wallet",
            {"head": ".page-head", "status": ".alarm", "whatToDo": ".alarm a.btn-danger"},
        )

        visit(page, self.url(f"/wallets/{wallet}/recover"))
        located = page.locator("dl.located dd").all_inner_texts()
        if not located:
            raise SystemExit("the recovery page shows no located funds: is the trace finished?")
        values["recover"] = {"located": located, "reached": text(page, "#step-find .r-body > p")}
        steps = {f"step{i}": f".steps-list > .r-step:nth-child({i})" for i in range(1, 5)}
        recover = {
            **steps,
            "head": ".page-head",
            "download": ".page-head a.btn",
            "timeline": ".timeline",
            "located": "dl.located",
            "pdf": ".steps-list a.btn:has-text('Incident report')",
        }
        self.shoot(page, "owner-recover", recover)
        self.shoot(page, "owner-recover-full", recover, full=True)

        visit(page, self.url("/notifications"))
        item = LOCATED
        if page.locator(item).count() == 0:
            raise SystemExit(f"alice has no 'Stolen funds located' notification for {FOCUS_TAG}")
        head = box(page, f"{item} .x-head")
        page.mouse.move(head["x"] + head["w"] - 140, head["y"] + head["h"] / 2)
        settle(page)
        tx_href = page.locator(f"{item} .x-more dd a").first.get_attribute("href") or ""
        values["notification"] = {
            "title": "Stolen funds located",
            "message": text(page, f"{item} .x-more p"),
            "tx": tx_href.rstrip("/").split("/")[-1],
        }
        self.shoot(
            page,
            "owner-notifications",
            {"item": item, "message": f"{item} .x-more p", "tx": f"{item} .x-more dd a"},
            cursor=True,
        )
        page.mouse.move(*NEUTRAL)

        visit(page, self.url(f"/wallets/{wallet}/verify"))
        self.shoot(page, "owner-verify", {"head": ".page-head", "status": ".alarm, section.panel"})
        state = ctx.storage_state()
        ctx.close()
        return state

    # ----- analyst ---------------------------------------------------------------------

    def analyst(self, who: tuple[str, str], trace_id: int, deposit: str) -> Any:
        ctx = self.context()
        page = self.login(ctx, who)
        values = self.manifest["values"]

        visit(page, self.url(f"/analyst/traces/{trace_id}"))
        if page.locator(".flow").count() == 0:
            raise SystemExit(f"trace {trace_id} is not finished (no hop graph on the page)")
        graph = page.evaluate(GRAPH, FOCUS_TAG)
        if graph is None or graph["mule"] is None:
            raise SystemExit(f"trace {trace_id} has no node for tag {FOCUS_TAG}")
        transfers = "section.panel:has(h2:text-is('Tainted transfers'))"
        values["trace"] = {
            "id": trace_id,
            "title": text(page, ".page-head h1"),
            "from": text(page, ".page-head p"),
            "stolen": text(page, ".panel-head .actions .muted"),
            "hops": graph["hops"],
            "transfers": text(page, f"{transfers} .panel-head .muted"),
            "labels": graph["labels"],
            "endpoints": [
                [" ".join(c.split()) for c in row.locator("td").all_inner_texts()[:5]]
                for row in page.locator("section.panel:has(h2:text-is('Endpoints')) tbody tr").all()
            ],
            "nodes": graph["nodes"],
            "exchange": graph["exchange"],
            "mule": graph["mule"],
        }
        nodes = {n["id"]: n["id"] for n in graph["nodes"]}
        trace_boxes = {
            "graph": ".flow",
            "panel": "section.panel:has(.flow)",
            "exchange": graph["exchange"],
            "exchangeName": f"{graph['exchange']} .flow-name",
            "exchangeValue": f"{graph['exchange']} .flow-value",
            "exchangeCard": graph["exchange"].replace("#n-", "#card-") + " rect",
            "mule": graph["mule"],
            "muleCard": graph["mule"].replace("#n-", "#card-") + " rect",
            "endpoints": "section.panel:has(h2:text-is('Endpoints'))",
            "transfers": transfers,
            **nodes,
        }
        self.shoot(page, "analyst-trace", trace_boxes)
        self.shoot(page, "analyst-trace-full", trace_boxes, full=True)
        mule = center(page, graph["mule"])
        page.mouse.move(VIEW["width"] - 1, VIEW["height"] - 70)
        page.mouse.move(*mule, steps=8)
        settle(page)
        self.shoot(page, "analyst-trace-hover", trace_boxes, cursor=True)
        page.mouse.move(*center(page, graph["exchange"]), steps=6)
        settle(page)
        self.shoot(page, "analyst-trace-exchange", trace_boxes, cursor=True)
        page.mouse.move(*NEUTRAL)
        self.keep_static(ctx)

        visit(page, self.url("/analyst/findings"))
        values["findings"] = page.locator("section.panel tbody tr").count()
        self.shoot(page, "analyst-findings", {"head": ".page-head", "table": "section.panel"})

        visit(page, self.url("/flags"))
        values["flags"] = page.locator(
            "section.panel:has(h2:text-is('All active flags')) tbody tr"
        ).count()
        self.shoot(
            page,
            "analyst-flags",
            {
                "head": ".page-head",
                "form": "section.panel:has(h2:text-is('Flag an account'))",
                "list": "section.panel:has(h2:text-is('All active flags'))",
            },
        )

        visit(page, self.url("/analyst/settings"))
        self.shoot(
            page,
            "analyst-settings",
            {"head": ".page-head", "first": "#settings-form section.panel"},
        )

        visit(page, self.url(f"/transactions?hash={deposit}"))
        values["lookup"] = text(page, "section.panel:has(dl.kv) .panel-head")
        self.shoot(
            page,
            "analyst-lookup",
            {
                "head": ".page-head",
                "search": "form[role=search]",
                "result": "section.panel:has(dl.kv)",
            },
        )
        state = ctx.storage_state()
        ctx.close()
        return state

    # ----- signed out, explorer --------------------------------------------------------

    def register(self) -> None:
        ctx = self.context()
        page = ctx.new_page()
        visit(page, self.url("/register"))
        self.shoot(page, "auth-register", {"card": "form", "title": "h2"})
        ctx.close()

    def explorer(self, deposit: str) -> None:
        ctx = self.browser.new_context(viewport=VIEW, device_scale_factor=2)  # no ngrok header
        page = ctx.new_page()
        page.goto(EXPLORER.format(deposit))
        page.get_by_text(FOCUS_TAG).first.wait_for(timeout=90_000)
        page.wait_for_load_state("networkidle")
        reject = page.get_by_role("button", name="Reject Non-Essential")
        if reject.count():  # the cookie banner covers the top of the page
            reject.first.click()
        page.wait_for_timeout(1500)
        status = "text=tesSUCCESS" if page.locator("text=tesSUCCESS").count() else "text=Success"
        file = "explorer-deposit.png"
        page.screenshot(path=OUT / file)
        self.manifest["values"]["explorer"] = {
            "tag": page.locator(f"text={FOCUS_TAG}").count() > 0,
            "status": status.removeprefix("text="),
        }
        self.manifest["captures"].append(
            {
                "file": file,
                "kind": "explorer",
                "page": f"testnet.xrpl.org/transactions/{deposit}",
                "size": VIEW,
                "scale": 2,
                "boxes": {
                    "tag": box(page, f"text={FOCUS_TAG}"),
                    "status": box(page, status),
                    "row": box(page, "text=Destination >> xpath=.."),
                },
            }
        )
        print(f"ok  testnet.xrpl.org deposit page -> {file}")
        ctx.close()

    # ----- recordings ------------------------------------------------------------------

    def record_trace(self, state: Any, trace_id: int) -> None:
        """Hop h pops at h * HOP_MS, the mule is hovered one hop after the last one, and the
        pointer lands on the exchange the hop after that (bar 20 beat 1 in the film)."""
        ctx = self.context(state, video=True)
        ctx.add_init_script(RETIME)
        page = ctx.new_page()
        created = page.evaluate("performance.timeOrigin")  # Chrome's clock; the video starts here
        page.goto(self.url(f"/analyst/traces/{trace_id}"), wait_until="domcontentloaded")
        page.wait_for_function(
            "document.getAnimations().some(a => "
            "a.effect?.target?.classList?.contains('flow-node') && a.startTime !== null)"
        )
        origin = page.evaluate("performance.timeOrigin")
        start = page.evaluate(
            "document.getAnimations().find(a => "
            "a.effect?.target?.classList?.contains('flow-node')).startTime"
        )
        graph = page.evaluate(GRAPH, FOCUS_TAG)
        last = graph["hops"] * HOP_MS

        def at(ms: float) -> None:  # wait for `ms` after the first pop, on the page's own clock
            page.wait_for_timeout(
                max(0, start + ms - page.evaluate("document.timeline.currentTime"))
            )

        def now() -> float:
            return origin + page.evaluate("document.timeline.currentTime")

        marks = {"flowStart": origin + start}
        at(last + 900)
        marks["moveStart"] = now()
        mule = center(page, graph["mule"])
        glide(page, (VIEW["width"] - 1, VIEW["height"] - 70), mule, 1100)
        marks["muleHover"] = now()
        at(last + 1.7 * HOP_MS)
        marks["exchangeMove"] = now()
        glide(page, mule, center(page, graph["exchange"]), 600)
        marks["exchangeHover"] = now()
        at(last + 3.75 * HOP_MS)
        marks["end"] = now()
        marks = {k: v / 1000 for k, v in marks.items()}
        boxes = {n["id"]: box(page, n["id"]) for n in graph["nodes"]}
        boxes |= {
            "graph": box(page, ".flow"),
            "panel": box(page, "section.panel:has(.flow)"),
            "exchange": box(page, graph["exchange"]),
            "exchangeName": box(page, f"{graph['exchange']} .flow-name"),
            "exchangeValue": box(page, f"{graph['exchange']} .flow-value"),
            "mule": box(page, graph["mule"]),
        }
        self.record("rec-trace", page, created / 1000, marks, boxes)
        self.manifest["captures"][-1] |= {
            "page": f"/analyst/traces/{trace_id}",
            "hopSeconds": HOP_MS / 1000,
            "hops": graph["hops"],
        }

    def record_what_to_do(self, state: Any, wallet: str) -> None:
        ctx = self.context(state, video=True)
        page = ctx.new_page()
        started = time.time()
        visit(page, self.url("/"))
        button = ".alarm a.btn-danger"
        boxes = {"status": box(page, ".alarm"), "whatToDo": box(page, button)}
        marks = {"ready": time.time()}
        page.wait_for_timeout(600)
        marks["moveStart"] = time.time()
        spot = center(page, button)
        glide(page, (VIEW["width"] - 1, 640), spot, 1300)
        marks["arrive"] = time.time()
        page.wait_for_timeout(350)
        with page.expect_navigation():
            marks["click"] = time.time()
            page.mouse.down()
            page.wait_for_timeout(110)
            page.mouse.up()
        settle(page)
        page.mouse.move(spot[0] + 1, spot[1])  # the new page's pointer, where the click was
        if not path_of(page).endswith(f"/wallets/{wallet}/recover"):
            raise SystemExit(f"'What to do' led to {path_of(page)}")
        marks["recover"] = time.time()
        page.wait_for_timeout(1500)
        marks["end"] = time.time()
        self.record("rec-what-to-do", page, started, marks, boxes)
        self.manifest["captures"][-1]["page"] = "/"

    def record_notification(self, state: Any) -> None:
        ctx = self.context(state, video=True)
        page = ctx.new_page()
        started = time.time()
        visit(page, self.url("/notifications"))
        item = LOCATED
        head = box(page, f"{item} .x-head")
        marks = {"ready": time.time()}
        page.wait_for_timeout(600)
        marks["moveStart"] = time.time()
        target = (head["x"] + head["w"] - 140, head["y"] + head["h"] / 2)
        glide(page, (VIEW["width"] - 1, 900), target, 1200)
        marks["hover"] = time.time()
        settle(page)
        boxes = {"item": box(page, item), "message": box(page, f"{item} .x-more p")}
        page.wait_for_timeout(3000)
        marks["end"] = time.time()
        self.record("rec-notification", page, started, marks, boxes)
        self.manifest["captures"][-1]["page"] = "/notifications"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=int, default=1, help="trace id (default 1)")
    parser.add_argument(
        "--explorer-only", action="store_true", help="redo only the testnet.xrpl.org screenshot"
    )
    args = parser.parse_args()
    if args.explorer_only:  # public site: works after the tunnel is gone
        manifest = json.loads((OUT / "manifest.json").read_text())
        manifest["captures"] = [c for c in manifest["captures"] if c["kind"] != "explorer"]
        with sync_playwright() as p:
            browser = p.chromium.launch(env=browser_env())
            cap = Capture("", browser)
            cap.manifest = manifest
            cap.explorer(manifest["values"]["notification"]["tx"])
            browser.close()
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    base = os.environ.get("TRAILER_BASE_URL", "").rstrip("/")
    if not base:
        raise SystemExit("TRAILER_BASE_URL is not set")
    user, analyst = creds("TRAILER_USER"), creds("TRAILER_ANALYST")
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        health = p.request.new_context(extra_http_headers=NGROK)
        response = health.get(f"{base}/healthz")
        if not response.ok:
            raise SystemExit(f"/healthz: HTTP {response.status}")
        print(f"ok  /healthz {response.text().strip()[:60]}")
        health.dispose()

        browser = p.chromium.launch(env=browser_env())
        cap = Capture(base, browser)

        def save() -> None:
            text = json.dumps(cap.manifest, indent=2, ensure_ascii=False)
            (OUT / "manifest.json").write_text(text)

        owner_state = cap.owner(user)
        values = cap.manifest["values"]
        deposit = values["notification"]["tx"]
        save()
        analyst_state = cap.analyst(analyst, args.trace, deposit)
        cap.register()
        save()
        cap.record_trace(analyst_state, args.trace)
        cap.record_what_to_do(owner_state, values["wallet"])
        cap.record_notification(owner_state)
        save()
        print("app captures done: the tunnel can close")
        cap.explorer(deposit)  # public explorer, no tunnel needed
        browser.close()

    shutil.rmtree(OUT / "_video", ignore_errors=True)
    save()
    print(json.dumps(values, indent=2, ensure_ascii=False))
    print(f"{len(cap.manifest['captures'])} captures in {OUT.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
