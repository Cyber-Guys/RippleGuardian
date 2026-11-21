"""Browser walkthrough of both roles against a running app (after `make demo`).

Logs in through the real form, visits every page, flags the first mule from the trace page
as the analyst, then checks as the user that the flag is visible. Saves screenshots.

    uv run --with playwright python scripts/e2e_browser.py \
        --user alice:PASSWORD --analyst analyst:PASSWORD [--chrome /path/to/chrome]

Playwright is not a project dependency: `--with` pulls it in for this run only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

OUT = Path("artifacts/screenshots")


def login(page: Page, base: str, credentials: str) -> None:
    name, password = credentials.split(":", 1)
    page.goto(f"{base}/login")
    page.fill("#username", name)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def shoot(page: Page, base: str, path: str, name: str) -> None:
    response = page.goto(f"{base}{path}")
    if response is None or response.status != 200:
        raise SystemExit(f"{path}: HTTP {response.status if response else 'no response'}")
    page.wait_for_timeout(1200)  # let the entrance motion settle
    page.screenshot(path=OUT / f"{name}.png", full_page=True)
    print(f"ok  {path:<32} -> {OUT / name}.png")


def main(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, args=["--no-sandbox"])

        analyst = browser.new_page(viewport={"width": 1440, "height": 900})
        analyst.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        login(analyst, args.base, args.analyst)
        shoot(analyst, args.base, "/analyst", "analyst-1-overview")
        shoot(analyst, args.base, "/analyst/findings", "analyst-2-findings")
        shoot(analyst, args.base, "/analyst/traces/1", "analyst-3-trace")
        rows = analyst.locator("tr:has(summary)")
        if rows.count():  # flag the first unflagged, unlabelled endpoint
            row = rows.first
            flagged = row.locator("a.mono").first.get_attribute("title")
            row.locator("summary").click()
            row.locator("select[name=category]").select_option("theft")
            row.locator("input[name=reason]").fill("Mule account: forwarded stolen XRP")
            row.locator("button[type=submit]").click()
            analyst.wait_for_load_state("networkidle")
        else:  # every endpoint already flagged by an earlier run: reuse one
            analyst.goto(f"{args.base}/flags")
            flagged = analyst.locator("table a.mono").first.get_attribute("title")
        print(f"ok  analyst flagged {flagged}")

        user = browser.new_page(viewport={"width": 1440, "height": 900})
        user.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        login(user, args.base, args.user)
        shoot(user, args.base, "/", "user-1-wallets")
        wallet = user.locator("a.wallet-card").first.get_attribute("href")
        shoot(user, args.base, wallet or "/", "user-2-wallet")
        shoot(user, args.base, f"{wallet}/recover", "user-3-recover")
        pdf = user.request.get(f"{args.base}{wallet}/report.pdf")
        if not pdf.body().startswith(b"%PDF"):
            raise SystemExit("incident report is not a PDF")
        (OUT / "incident-report.pdf").write_bytes(pdf.body())
        print(f"ok  incident report -> {OUT / 'incident-report.pdf'}")
        shoot(user, args.base, "/notifications", "user-3b-notifications")
        shoot(user, args.base, f"/flags?q={flagged}", "user-4-check-address")
        if "Flagged as theft" not in user.content():
            raise SystemExit("the analyst's flag is not visible to the user")
        print("ok  user sees the analyst's flag")
        if errors:
            raise SystemExit(f"browser console errors: {errors}")
        if user.goto(f"{args.base}/analyst/findings").status != 403:
            raise SystemExit("a user could open an analyst page")
        print("ok  user gets 403 on analyst pages")
        browser.close()
    print("e2e ok: no console errors on any page")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--user", required=True, help="username:password")
    parser.add_argument("--analyst", required=True, help="username:password")
    parser.add_argument("--chrome", default=None, help="Chromium binary (default: Playwright's)")
    sys.exit(main(parser.parse_args()))
