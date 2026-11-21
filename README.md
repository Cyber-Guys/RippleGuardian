<p align="center">
  <img src="docs/assets/logo.jpeg" width="180" alt="Ripple Guardian logo">
</p>

<h1 align="center">Ripple Guardian</h1>

<p align="center">
  Wallet protection and theft tracing for the XRP Ledger.<br>
  IXH26 Bari · Track 2, XRPL applications · built 20 to 21 November 2026
</p>

<p align="center">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3776AB">
  <img alt="XRPL Testnet" src="https://img.shields.io/badge/XRPL-Testnet-0A84FF">
  <img alt="Tests" src="https://img.shields.io/badge/tests-75%20offline-2EA44F">
</p>

When an XRPL seed leaks, a thief adds their own signing key, empties the wallet and pushes the money through fresh accounts to an exchange, often within minutes. Tracing services exist, but they are sold to exchanges and police, so the owner finds out late and has nothing to show anyone. Ripple Guardian watches wallets for the people who own them. It tells the owner in plain words when a key changes or funds leave, walks them through recovery, and follows the stolen XRP hop by hop to the exchange and the destination tag that received it: the one number an exchange needs to find the customer. Analysts review what the detectors raise and publish accountable flags that every user can check before sending money.

Everything in the demo runs on XRPL Testnet with real, validated transactions.

<p align="center">
  <img src="artifacts/screenshots/analyst-hop-graph.png" width="860" alt="Hop graph of a traced theft: victim, attacker, two relays, five mules, two exchanges">
</p>

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [Claims and evidence](#claims-and-evidence)
- [What is simulated](#what-is-simulated)
- [Roadmap](#roadmap)
- [Team](#team)
- [Documentation](#documentation)

## What it does

### For wallet owners

- **Sign up without personal data.** A username and a password. No email, no phone number.
- **Watch any number of addresses.** A worker follows them live over WebSocket and polls the ledger to recover anything the stream missed.
- **Get alerts that say what happened.** The owner is notified when the wallet's signing setup changes (new regular key, signer list, master key disabled, account deleted), when money leaves above a threshold they set, and when the wallet deals with an address or transaction an analyst has flagged. Each alert type can be switched off per wallet.
- **Recover after a theft.** A four-step screen: lock the wallet, move what is left, find the money, report it. The owner can ask for a trace with one click and download a PDF incident report with every transaction link and a SHA-256 fingerprint of the evidence.
- **Learn where the money went.** When a trace finishes, the owner is told which exchange received the funds, under which destination tag, and how much.
- **Check an address before paying.** Any user can look up an address and see whether an analyst flagged it, by whom and why.

### For analysts

- **Findings queue.** Four detectors run on the history of watched wallets. Possible takeover (a key change followed by a drain to new destinations) and funds funnel (several accounts forwarding to the same exchange tag) fire on live Testnet data. Wash trading and liquidity drop are built and tested, waiting on DEX and AMM data.
- **Taint tracing.** From a takeover finding or a robbed wallet, the analyst starts a trace. The result is an animated hop graph: each account shows the tainted amount it received and its share of the theft, link width follows value, and hovering an account highlights its money path.
- **Accountable flags.** Flags carry the analyst's name, a category and a reason, can be revoked, and are visible to every user.

<p align="center">
  <img src="artifacts/screenshots/user-3-recover.png" width="420" alt="Recovery screen for a robbed owner">
  <img src="artifacts/screenshots/analyst-2-findings.png" width="420" alt="Analyst findings queue">
</p>

## How it works

```
                         docker compose
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  browser ──cookie──▶ api (FastAPI, Jinja2 + HTMX)                │
 │                        │  owner pages     analyst pages          │
 │                        ▼                                         │
 │                    Postgres ◀──────── worker ──── WebSocket ─────┼──▶ XRPL Testnet
 │                    (store/)           │  monitor + detectors     │    (subscribe,
 │                                       │  trace jobs   ─ JSON-RPC ┼──▶  account_tx)
 └──────────────────────────────────────────────────────────────────┘
```

The worker is the only process that talks to the ledger. The web app never calls XRPL and works only with the database, so a slow Testnet node never blocks a page.

```
src/ixh26/
  ledger/   the only code that imports xrpl-py: reader, stream, normalisation, submit helper
  core/     pure logic with no I/O: alert rules, haircut taint, four detectors
  flows/    glue: monitor, trace jobs, worker loops, incident report, offline smoke run
  store/    SQLAlchemy tables and queries
  app/      web pages and JSON API; never signs, never calls XRPL
```

### The trace

- **Haircut taint in ledger order.** When stolen XRP lands in an account that already held clean funds, every later payment out of it carries a proportional share of the taint. The opening balance is read at the ledger before the theft, and payments made before the stolen funds arrived carry none.
- **Delivered amounts only.** Every amount comes from `delivered_amount`, as integer drops. A partial payment can ask for 1,000 XRP and deliver 0.01; the trace counts 0.01.
- **Bounded.** A branch stops at a labelled entity such as an exchange, below 1% of the theft or 1 XRP, or after 6 hops. All three limits are configurable.
- **Ends at a customer, not a hot wallet.** At an exchange the result is split by destination tag, which identifies one customer account.

### Problems we solved

- **Lost WebSocket messages.** A polling loop reads each wallet from its ledger cursor, so a missed payment still raises its alert. A newly added wallet backfills its history silently, so the owner is not flooded with alerts about the past.
- **Fake amounts.** Partial payments make the `Amount` field lie. The ledger reader refuses a payment without `delivered_amount`.
- **Mixing with clean funds.** Haircut taint dilutes honestly instead of attributing all of a mule's outflow to the theft.

More detail, with code excerpts, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quickstart

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker.

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

`make demo` creates two faucet wallets the first time (seeds go straight into `.env`), then runs a theft on Testnet:

1. the attacker sets their own regular key on the victim
2. drains 99.99997 XRP to a fresh account
3. splits it across two relays, which feed five mules
4. three mules deposit at Exchange under tag 777001, one at Exchange B under tag 4242, and one keeps its share

Sign in as `alice` to see the alerts and the recovery screen, and as `analyst` to see the findings and the trace.

Without Docker, set `DATABASE_URL=sqlite:///data/guardian.db` in `.env` and run `make api` and `make worker` in two terminals. Exchanges are added with `ixh26 label <address> --name <name>`.

On WSL, Python DNS lookups can stall on IPv6 and make every Testnet call time out. Prefix the command with `RES_OPTIONS="timeout:1 attempts:1"` if that happens.

## Claims and evidence

| Claim | Evidence |
|---|---|
| A real theft on Testnet is detected, traced and explained to the owner | [docs/E2E.md](docs/E2E.md), `artifacts/tx_log.jsonl`, `artifacts/screenshots/` |
| A laundering tree (2 relays, 5 mules, 2 exchanges) is traced over 4 hops: 12 tainted transfers, 55% located at Exchange tag 777001, 22% at Exchange B tag 4242, 15% held by a mule | run 2 in [docs/E2E.md](docs/E2E.md); rekey [F60AA3C4…](https://testnet.xrpl.org/transactions/F60AA3C4C14EE016BBD26D5BEF208146AAA9545640D526318E897D12CEE1FF10), drain [5824D3C4…](https://testnet.xrpl.org/transactions/5824D3C46D3B223031BFFD93364BDD6A102AC3A91C9EE80C029EFB749430AECB), deposits [7758D5E4…](https://testnet.xrpl.org/transactions/7758D5E4C3C8BE47CA4C51167183E0C3380CB448BACF775A42741D432C00C29C), [2E42BD03…](https://testnet.xrpl.org/transactions/2E42BD03C6417115DF303F0BD9F8E95B56DD33B5CA326459352FF697752C5F72), [00C94FE3…](https://testnet.xrpl.org/transactions/00C94FE3890E8896696F447A26A91841352B48DC6C1190A5DF63E61B159FF566), [F995F492…](https://testnet.xrpl.org/transactions/F995F492813FE51D07A89B95D1A3FEA380995BDF34ED082FAE9BBFF9C71D5FC0) |
| The trace matches the ledger: 7 of 7 edges agree with `tx` (sender, receiver, tag, delivered amount) | run 1 in [docs/E2E.md](docs/E2E.md), drain [9C004106…](https://testnet.xrpl.org/transactions/9C004106BB908901B1B328AD82272EA253D1EB2C116F1146553D1018A7EB4E) |
| Amounts come from `delivered_amount`, so partial payments cannot inflate them | `tests/ledger/test_ledger_normalize.py::test_partial_payment_reports_delivered_not_requested_amount` |
| Haircut taint follows ledger order, dilutes with clean funds and stops at 1% or the hop limit | `tests/core/test_taint.py` |
| Owners hear about key changes, outgoing payments and flagged counterparties, within their own settings | `tests/core/test_alerts.py`, `tests/flows/test_flows.py` |
| A missed WebSocket message is caught up by polling, without alerting on old history | `tests/flows/test_flows.py::test_polling_backfills_silently_then_catches_up_with_alerts` |
| A robbed owner gets a 4-step recovery screen, can ask for a trace, and downloads a PDF report with every tx link and a SHA-256 fingerprint | `tests/flows/test_report.py`, `tests/app/test_web.py::test_owner_can_request_a_trace_of_their_theft`, `artifacts/screenshots/incident-report.pdf` |
| Users can't open analyst pages; analyst flags are visible to users | `tests/app/test_web.py`, `scripts/e2e_browser.py` run in [docs/E2E.md](docs/E2E.md) |
| Takeover and funnel detectors fire on live Testnet data | findings in [docs/E2E.md](docs/E2E.md); rules in `tests/core/test_detection.py` |
| Testnet is the default. Mainnet is opt-in with `XRPL_NETWORK=mainnet`, needs its own database and never submits a transaction. Any validated transaction can be looked up by hash on either network | `tests/test_config.py`, `tests/app/test_transaction_api.py`, `tests/store/test_network_store.py` |
| A user can prove control of a watched wallet with a one-drop payment that carries a one-time destination tag, valid for 15 minutes (API only, no web page yet) | `tests/app/test_verification.py` |
| Amounts are never floats and seeds can't be committed | `tests/test_contracts.py`, `tests/test_secret_scan.py` |

## What is simulated

- Exchange and Exchange B are Testnet wallets we control, shown as "SIMULATED" in the app. Real exchanges would be added as labels with `ixh26 label`.
- The theft is scripted by `scripts/demo.py`. Its transactions are real and validated on Testnet.
- `make smoke` and the offline tests use synthetic addresses and hashes, marked `SIMULATED` in the code. They never appear in the app or in the evidence.
- The wash trading and liquidity drop detectors are built and tested, but the ledger reader does not yet extract DEX fills or AMM withdrawals, so they get no live data.

## Roadmap

- Ask the issuer to freeze or claw back stolen tokens (trust line freeze, Clawback), using the trace as evidence.
- A web page for wallet ownership proof. The API is built (`/api/wallets/{address}/verification`); the page and the badge on the wallet card are not.
- Read DEX fills and AMM withdrawals, so all four detectors run live and taint can follow funds across currencies.
- Opt-in push or email delivery.
- Mainnet in the web app. The backend can watch and trace on Mainnet, read-only, but the demo and all evidence stay on Testnet until the evidence format has been reviewed with an exchange.

## Team

Team CyberGuys on the IXH26 platform.

- Nicola Ghisu (NicoXVI)
- Tommaso Casti (t0mm1)
- Daniele Orrù (DenInDev)
- Andrea Cerolini (percyghost)
- Diego Oliva (doliv)
- Nicholas Meli (uNickz)

We all worked on every part of the project. The commit history comes from fewer laptops than people, so it does not show who did what.

Built with AI coding assistants, declared in [docs/SUBMISSION.md](docs/SUBMISSION.md).

## Documentation

| File | For | What it covers |
|---|---|---|
| [docs/CONTEXT.md](docs/CONTEXT.md) | newcomers, human or agent | the idea, how it changed during the night, glossary |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | developers | modules, data flow, the code behind each step |
| [docs/DESIGN.md](docs/DESIGN.md) | judges, reviewers | threat model and known limits |
| [docs/E2E.md](docs/E2E.md) | judges | the Testnet runs, checked against the ledger and in a browser |
| [docs/DECISIONS.md](docs/DECISIONS.md) | team | every decision with its reason |
| [docs/SUBMISSION.md](docs/SUBMISSION.md) | organisers | submission text, third-party summary, AI disclosure |
| [CLAUDE.md](CLAUDE.md) | AI agents | the rules every agent working on this repo follows |
| [THIRD_PARTY.md](THIRD_PARTY.md) | everyone | every library and asset with its licence |
