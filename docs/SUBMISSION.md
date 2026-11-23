# Submission: IXH26 Track 2 (XRPL applications)

Text for the hackathon app. A human submits it before Sat 21 Nov 12:00 CET (target 11:30) and fills in the fields marked TODO. Every claim below has evidence in the README's claims table.

## Platform fields

| Field | Value |
|---|---|
| Project name | Ripple Guardian |
| Track | XRPL applications |
| Repository | https://github.com/Cyber-Guys/RippleGuardian |
| Demo video | Trailer, 90 s: https://github.com/Cyber-Guys/RippleGuardian/blob/main/docs/trailer/out/trailer.mp4 (30 s cut: https://github.com/Cyber-Guys/RippleGuardian/blob/main/docs/trailer/out/trailer-30s.mp4) |
| Slides | TODO |
| SourceTag | none assigned; transactions use the team constant 26112026 (see `config.py`) |

## Short description (max 200 characters)

```text
Ripple Guardian is a blockchain forensics framework for the XRP Ledger: it alerts owners when keys change or funds leave, and traces stolen XRP hop by hop to the exchange and destination tag.
```

## Description (max 5000 characters, markdown)

```markdown
## The problem

When an XRPL seed leaks, a thief can add their own signing key, empty the wallet and move the money through fresh accounts to an exchange within minutes. Tracing services exist, but they sell to exchanges and police. The owner usually finds out late, from their balance, and has nothing to show anyone.

## What Ripple Guardian does

Ripple Guardian is a blockchain forensics framework for the XRP Ledger, built for the people who own the wallets. One web app with two roles: wallet owners and analysts.

### For owners

Owners sign up with a username, no email or personal data, and add the addresses they want watched. A worker follows those wallets over WebSocket and falls back to polling for anything the stream misses. The owner gets a notification in plain words when:

- the wallet's signing setup changes: a new regular key, a signer list, the master key disabled, or the account deleted
- money leaves above a threshold they choose
- the wallet deals with an address or transaction an analyst has flagged

Each kind of alert can be switched off per wallet.

A robbed owner sees a four-step recovery screen, can ask for a trace, and can download a PDF incident report with every transaction link and a SHA-256 fingerprint of the evidence, ready to hand to an exchange or the police. When the trace finishes, the owner is told which exchange received the money, under which destination tag, and how much.

### For analysts

Analysts see what the detectors raised. Two run on live Testnet data: takeover (a key change followed by a drain to new destinations) and funnel (several accounts forwarding to the same exchange destination tag). Wash trading and liquidity drop detectors are also built and tested; they will get live data once the ledger reader extracts DEX fills and AMM withdrawals.

From a takeover finding, an analyst starts a trace and gets an animated hop graph from the victim to the exchanges. Each account shows the tainted amount it received and its share of the theft, links get thicker as more value flows through them, and hovering an account highlights its money path. Analysts flag addresses or transactions with a category and a reason. Any user can look up an address before sending money and see who flagged it and why.

## How the trace works

- Haircut taint in ledger order. When stolen XRP lands in an account that already held clean funds, each later payment out of it carries a proportional share of the taint. Payments made before the theft carry none.
- Amounts come from `delivered_amount`, never `Amount`, so a partial payment cannot inflate a trace.
- The trace stops at a known exchange, when the tainted amount falls below 1% of the theft (or 1 XRP), or after 6 hops. All limits are configurable.
- At an exchange it reports the destination tag, the one number the exchange needs to find the customer who received the money.

## A real theft on Testnet

`make demo` runs a scripted theft made of real, validated Testnet transactions. The attacker sets their own regular key on the victim, drains 99.99997 XRP, splits it across two relays that feed five mules, and cashes out at two exchanges.

In our latest run the trace followed 12 tainted transfers over 4 hops and found:

- 54.94 XRP (55%) at Exchange, destination tag 777001
- 21.98 XRP (22%) at Exchange B, destination tag 4242
- 15.38 XRP (15%) still held by one mule

In an earlier run all 7 traced transfers matched the ledger's own record: sender, receiver, tag and delivered amount. The owner was notified of the key change, of the drain and of the trace result, and the analyst saw a takeover finding on the victim and a funnel finding on the exchange tag.

Transaction hashes, screenshots and the browser check are in the repo (`docs/E2E.md`, `artifacts/tx_log.jsonl`).

## What is simulated

- Both exchanges are Testnet wallets we control, labelled "SIMULATED" in the app.
- The theft is scripted. Its transactions are real.

## Next

- Use the trace as evidence to ask a token issuer to freeze or claw back stolen tokens.
- Read DEX fills and AMM withdrawals, so all four detectors run live and the trace can follow funds across currencies.
```

## Technical description (max 1000 characters, markdown)

```markdown
Python 3.12 with xrpl-py, FastAPI, Jinja2 + HTMX, SQLAlchemy on Postgres and fpdf2, run with Docker Compose.

Only the worker talks to XRPL. It subscribes to watched accounts over WebSocket and uses JSON-RPC `account_tx` for history and traces. The web app never calls the ledger and works only with the database, so a slow Testnet node never blocks a page. `ledger/` is the only module that imports xrpl-py; `core/` holds alert rules, haircut taint and the four detectors as pure functions with no I/O, tested offline.

Problems we had to solve:

- WebSocket messages get lost. A polling loop reads from each wallet's ledger cursor, so a missed payment still raises its alert, while a newly added wallet backfills its history silently.
- Partial payments can fake the `Amount` field. Every amount comes from `delivered_amount`, as integer drops, never floats.
- Taint has to respect time. Funds are followed in ledger order, so payments sent before the theft carry none.
```

## How to run

```bash
make setup && docker compose up -d --build
docker compose exec api ixh26 create-user alice
docker compose exec api ixh26 create-user analyst --role analyst
DATABASE_URL=postgresql+psycopg://ixh26:ixh26@localhost:5432/ixh26 make demo ARGS="--watch-user alice --auto-trace analyst"
```

Then open http://localhost:8000. Full steps are in the README.

## Prior work

None. The repository was created during the hackathon (first commit Fri 20 Nov after 12:00 CET). `brainstorming/` holds the organisers' welcome slides and our notes for reference. TODO: team to confirm.

## Third-party software and assets

All listed with licences in `THIRD_PARTY.md`: xrpl-py, FastAPI, Uvicorn, SQLAlchemy, psycopg, redis-py (declared and configured, not used by the code yet), PyJWT, argon2-cffi, Jinja2, python-multipart, fpdf2 (with Pillow and fontTools as its dependencies), htmx 2.0.4 (vendored), Lucide icons (path data inlined), and the dev tools Ruff, pytest, pytest-asyncio and HTTPX. Playwright is used only to run the browser check, not shipped.

## AI tools used

- Claude Code (Claude Opus) as a coding agent: review of the idea, design of the backend, code for the ledger reader, taint engine, API, worker, web app and demo, tests, the end-to-end browser check, and these documents. A human approved every merge.
- Codex as a coding agent for the fraud detectors (T-006).
- Claude Code skills used along the way: superpowers (workflow), frontend-design, dataviz (palette validation), unslop by Damir Sokolovsky (CC BY 4.0, interface review), humanizer (wording of the docs).
- MCP servers: 21st.dev (looked at glass dashboard components for reference; no code copied) and graphify (code graph used to check the architecture description).

Commits carry no AI co-author trailer (policy 1.1, rule 17); this section is the single place where AI use is declared.

## Team

- Nicola Ghisu (NicoXVI)
- Tommaso Casti (t0mm1)
- Daniele Orrù (DenInDev)
- Andrea Cerolini (percyghost)
- Diego Oliva (doliv)
- Nicholas Meli (uNickz)

We all worked on every part of the project. The commit history comes from fewer laptops than people, so it does not show who did what.