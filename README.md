# XRPL Wallet Guardian

Wallet Guardian watches XRP Ledger wallets for the people who own them. When a wallet's signing keys change or its funds leave, the owner gets a notification in plain words with a short list of what to do next. Behind the scenes, analysts see what the detectors raised, trace stolen XRP hop by hop with a haircut taint model until it reaches an exchange and the exact destination tag, and publish flags that every user can look up before sending money. It runs on XRPL Testnet, and every demo transaction is real.

IXH26 Bari, Track 2 (XRPL applications). Built during the hackathon, 20 to 21 November 2026.

## How it fits together

```
                         docker compose
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  browser ──cookie──▶ api (FastAPI, Jinja2 + HTMX)                │
 │                        │  user pages      analyst pages          │
 │                        ▼                                         │
 │                    Postgres ◀──────── worker ──── WebSocket ─────┼──▶ XRPL Testnet
 │                    (store/)           │  monitor + detectors     │    (subscribe,
 │                                       │  trace jobs   ─ JSON-RPC ┼──▶  account_tx)
 └──────────────────────────────────────────────────────────────────┘

 src/ixh26/
   ledger/   the only code that talks to XRPL (reader, stream, submit helper)
   core/     pure logic: alert rules, haircut taint, four detectors (no I/O)
   flows/    glue: monitor, trace job, worker, offline smoke scenario
   store/    SQLAlchemy tables and queries
   app/      web pages and JSON API; never signs, never calls XRPL
```

The worker is the only process that reads the ledger. The web app only reads the database, so a slow or unreachable Testnet node never blocks a page. More detail, with code excerpts, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quickstart

```bash
make setup                         # uv sync, and .env from .env.example: put a JWT_SECRET in it
make check                         # lint, format, offline tests, secret scan
make smoke                         # the whole demo path offline, on SIMULATED data
docker compose up -d --build       # api on http://localhost:8000, worker, Postgres
docker compose exec api ixh26 create-user alice
docker compose exec api ixh26 create-user analyst --role analyst
DATABASE_URL=postgresql+psycopg://ixh26:ixh26@localhost:5432/ixh26 \
  make demo ARGS="--watch-user alice --auto-trace analyst"
```

`make demo` creates two faucet wallets the first time (seeds go straight into `.env`), then runs a theft on Testnet: it adds an attacker key to the victim, drains it, splits the money across three fresh mule accounts and deposits it at our exchange wallet under tag 777001. Sign in as `alice` to see the notifications and as `analyst` to see the findings and the trace.

Without Docker, set `DATABASE_URL=sqlite:///data/guardian.db` in `.env` and run `make api` and `make worker` in two terminals.

On WSL, Python DNS lookups can stall on IPv6 and make every Testnet call time out. If that happens, prefix the command with `RES_OPTIONS="timeout:1 attempts:1"`.

## Claims and evidence

| Claim | Evidence |
|---|---|
| A real theft on Testnet is detected, traced and explained to the owner | [docs/E2E.md](docs/E2E.md), `artifacts/tx_log.jsonl`, `artifacts/screenshots/` |
| The trace matches the ledger: 7 of 7 edges agree with `tx` (sender, receiver, tag, delivered amount) | [docs/E2E.md](docs/E2E.md), drain [9C004106…](https://testnet.xrpl.org/transactions/9C004106BB908901B1B328AD82272EA253D1EB2C116F1146553D1018A7EB4E) |
| 95.6% of the stolen XRP is attributed to the exchange, tag 777001 | trace 1 in [docs/E2E.md](docs/E2E.md); deposits [4D847C23…](https://testnet.xrpl.org/transactions/4D847C23561D914AF102B963C31A30F24C293839C13CFFD42D0CDACC4F1900EC), [22A892C1…](https://testnet.xrpl.org/transactions/22A892C1F7A0971654D9AF81347D081E5413F3DF1614C552B3EA154363F1C8A0), [6BF03F43…](https://testnet.xrpl.org/transactions/6BF03F43C6EC73E88B0751AFC6EFACA90020A7C5BE4F63AD6F042677D370028C) |
| Amounts come from `delivered_amount`, so partial payments cannot inflate them | `tests/ledger/test_ledger_normalize.py::test_partial_payment_reports_delivered_not_requested_amount` |
| Haircut taint follows time order, dilutes with clean funds and stops at 1% or the hop limit | `tests/core/test_taint.py` |
| The owner hears about key changes, outgoing payments and flagged counterparties, within their own settings | `tests/core/test_alerts.py`, `tests/flows/test_flows.py` |
| A missed WebSocket message is caught up by polling, without alerting on old history | `tests/flows/test_flows.py::test_polling_backfills_silently_then_catches_up_with_alerts` |
| Users can't open analyst pages; analyst flags are visible to users | `tests/app/test_web.py`, `scripts/e2e_browser.py` run in [docs/E2E.md](docs/E2E.md) |
| Takeover and funnel detectors fire on live Testnet data | findings in [docs/E2E.md](docs/E2E.md); rules in `tests/core/test_detection.py` |
| Mainnet is refused, amounts are never floats, seeds can't be committed | `tests/test_config.py`, `tests/test_contracts.py`, `tests/test_secret_scan.py` |

## What is simulated

- The exchange is a Testnet wallet we control, shown as "Exchange (SIMULATED)" in the app. Real exchanges would be added as labels with `ixh26 label`.
- The theft is scripted by `scripts/demo.py`. The transactions themselves are real and validated on Testnet.
- `make smoke` and the offline tests use synthetic addresses and hashes, marked `SIMULATED` in the code. They never appear in the app or in the evidence.
- The wash-trading and liquidity-drop detectors are built and tested, but the ledger reader does not yet extract DEX fills or AMM withdrawals, so they get no live data.

## Roadmap

- Ask the issuer to freeze or claw back stolen tokens (XRPL Clawback, trust line freeze), using the trace as evidence.
- Proof that a user owns a wallet: a tiny payment with a destination tag we assign.
- Read DEX fills and AMM withdrawals, so all four detectors run live and taint can follow funds across currencies.
- Push or email delivery, as an opt-in channel.
- Mainnet, once the evidence format has been reviewed with an exchange.

## Team

tommaso (repo skeleton, policy, contracts), daniele (fraud detectors), nico (ledger reader, taint, API, worker, web app, Testnet demo). Built with AI assistance, declared in [docs/SUBMISSION.md](docs/SUBMISSION.md).

## More documentation

- [docs/CONTEXT.md](docs/CONTEXT.md): the idea, how it changed during the night, and a glossary. Start here if you are new to the repo, human or agent.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): modules, data flow and the code behind each step.
- [docs/DESIGN.md](docs/DESIGN.md): threat model and known limits.
- [docs/DECISIONS.md](docs/DECISIONS.md): every decision with its reason.
- [docs/SUBMISSION.md](docs/SUBMISSION.md): the text for the hackathon platform.
- [CLAUDE.md](CLAUDE.md): the rules every agent working on this repo follows.
