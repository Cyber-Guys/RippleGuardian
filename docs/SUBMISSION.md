# Submission: IXH26 Track 2 (XRPL applications)

Draft text for the hackathon app. A human submits it before Sat 21 Nov 12:00 CET (target 11:30) and fills in the fields marked TODO. Every claim below has evidence in the README's claims table.

## Platform fields

| Field | Value |
|---|---|
| Project name | XRPL Wallet Guardian |
| Track | XRPL applications |
| Short description | Watches XRPL wallets for their owners, tells them in plain words when a key changes or funds leave, and traces stolen XRP hop by hop to the exchange and destination tag that received it. |
| Repository | https://github.com/Cyber-Guys/xrpl_hackathon (TODO: make it accessible to the judges) |
| Demo video | TODO |
| Slides | TODO |
| SourceTag | none assigned; transactions use the team constant 26112026 (see `config.py`) |

## Description

When an XRPL seed leaks, the thief adds a signing key, empties the wallet and pushes the money through new accounts to an exchange in a few minutes. Tracing services exist, but they are sold to exchanges and police; the owner finds out late and has nothing to show anyone.

Wallet Guardian is one web app with two roles. Owners add the addresses they want watched, with only a username and no personal data. A worker follows those wallets over WebSocket and polling. When a signing key changes, money leaves above the owner's threshold, or the wallet deals with an account an analyst has flagged, the owner gets a notification and a status with the steps to take now.

Analysts see what the detectors raised: a takeover (key change followed by a drain to new destinations) or a funnel (several accounts forwarding to the same exchange tag). They can start a trace. The tracer uses a haircut taint model in ledger order, reads `delivered_amount` so partial payments can't fake amounts, accounts for clean balances, and stops at known exchanges, reporting the destination tag: the one number an exchange needs to find the customer. The victim is notified with the exchange, the tag and the amount. Analysts publish flags with their name and reason, and every user can check an address against them before paying.

In our Testnet run, a 99.99997 XRP theft split across three mules was traced to the exchange under tag 777001 with 95.6% of the stolen value attributed, and every one of the 7 traced transfers matched the ledger's own record.

What is real and what is simulated: all demo transactions are real and validated on Testnet. The exchange is a wallet we control, labelled "Exchange (SIMULATED)". The theft is scripted.

## How to run

```bash
make setup && docker compose up -d --build
docker compose exec api ixh26 create-user alice
docker compose exec api ixh26 create-user analyst --role analyst
DATABASE_URL=postgresql+psycopg://ixh26:ixh26@localhost:5432/ixh26 make demo ARGS="--watch-user alice --auto-trace analyst"
```

Then open http://localhost:8000. Full steps are in the README.

## Prior work

None. The repository was created during the hackathon (first commit Fri 20 Nov after 12:00 CET). `brainstorming/` holds the organisers' welcome slides for reference. TODO: team to confirm.

## Third-party software and assets

All listed with licences in `THIRD_PARTY.md`: xrpl-py, FastAPI, Uvicorn, SQLAlchemy, psycopg, redis-py, PyJWT, argon2-cffi, Jinja2, python-multipart, htmx 2.0.4 (vendored), Lucide icons (path data inlined), and the dev tools Ruff, pytest, pytest-asyncio and HTTPX. Playwright is used only to run the browser check, not shipped.

## AI tools used

- Claude Code (Claude Opus) as a coding agent: review of the idea, design of the backend, code for the ledger reader, taint engine, API, worker, web app and demo, tests, the end-to-end browser check, and these documents. A human approved every merge.
- Codex as a coding agent for the fraud detectors (T-006).
- Claude Code skills used along the way: frontend-design, dataviz (palette validation), unslop by Damir Sokolovsky (CC BY 4.0, interface review), humanizer (wording of the docs).
- MCP servers: 21st.dev (looked at glass dashboard components for reference; no code copied) and graphify (code graph used to check the architecture description).

## Team

| Name | Role |
|---|---|
| Tommaso Casti | repo skeleton, policy, shared contracts, docker |
| Daniele Orrù | fraud detectors |
| Nico (NicoXVI) | ledger reader, taint tracer, API, worker, web app, Testnet demo, docs |
| doliv | TODO |
