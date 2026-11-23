<p align="center">
  <img src="docs/assets/banner.png" width="100%" alt="Ripple Guardian: blockchain forensics for the XRP Ledger">
</p>

<p align="center">
  <b>A blockchain forensics framework for the XRP Ledger: wallet protection and theft tracing.</b><br>
  <sub>IXH26 Italian XRPL Hackathon · Bari · Track 2, XRPL applications · built 20-21 November 2026 by team CyberGuys</sub><br>
  <a href="docs/trailer/out/trailer.mp4">▶ Watch the trailer (90 s)</a> · <a href="docs/trailer/out/trailer-30s.mp4">30 s cut</a>
</p>

<p align="center">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3776AB">
  <img alt="XRPL Testnet" src="https://img.shields.io/badge/XRPL-Testnet-0A84FF">
  <img alt="Tests" src="https://img.shields.io/badge/tests-75%20offline-2EA44F">
  <img alt="IXH26 Track 2" src="https://img.shields.io/badge/IXH26-Track%202-E0533A">
</p>

## Built at IXH26

<p align="center">
  <img src="docs/assets/ixh26.png" width="100%" alt="IXH26 Italian XRPL Hackathon, University of Bari Aldo Moro, 20–21 November 2026, Track 2: XRPL Applications">
</p>

Ripple Guardian was built in 24 hours at **IXH26**, the Italian XRPL Hackathon, held at the University of Bari Aldo Moro on 20 and 21 November 2026 and organised by XRPL Commons and De Componendis Cifris. Teams picked one of three tracks: advanced cryptography, XRPL applications and tokenisation.

We competed in **Track 2: XRPL applications**, the open track. There is no fixed theme: the brief is to *build something that meaningfully leverages the XRP Ledger*, whether payments, tokenisation, DeFi, identity or something new. Projects are judged on idea, implementation, demo quality and real-world potential. Prizes, rules and how we address each criterion are in [The hackathon](#the-hackathon).

## Team

Team **CyberGuys**, a hackathon team from Sardinia.

<p align="center">
  <a href="https://github.com/doliv8"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/doliv8-dark.png"><img src="docs/assets/team/doliv8-light.png" width="140" alt="Diego Oliva (@doliv8)"></picture></a>&nbsp;&nbsp;
  <a href="https://github.com/uNickz"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/uNickz-dark.png"><img src="docs/assets/team/uNickz-light.png" width="140" alt="Nicholas Meli (@uNickz)"></picture></a>&nbsp;&nbsp;
  <a href="https://github.com/AndreaCerolini"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/AndreaCerolini-dark.png"><img src="docs/assets/team/AndreaCerolini-light.png" width="140" alt="Andrea Cerolini (@AndreaCerolini)"></picture></a>
  <br><br>
  <a href="https://github.com/DenInDev"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/DenInDev-dark.png"><img src="docs/assets/team/DenInDev-light.png" width="140" alt="Daniele Orrù (@DenInDev)"></picture></a>&nbsp;&nbsp;
  <a href="https://github.com/NicoXVI"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/NicoXVI-dark.png"><img src="docs/assets/team/NicoXVI-light.png" width="140" alt="Nicola Ghisu (@NicoXVI)"></picture></a>&nbsp;&nbsp;
  <a href="https://github.com/T0mm1-byte"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/team/T0mm1-byte-dark.png"><img src="docs/assets/team/T0mm1-byte-light.png" width="140" alt="Tommaso Casti (@T0mm1-byte)"></picture></a>
</p>

We all worked on every part of the project. The commit history comes from fewer laptops than people, so it does not show who did what.

Built with AI coding assistants, declared in [docs/SUBMISSION.md](docs/SUBMISSION.md).

## What Ripple Guardian does

When an XRPL seed leaks, a thief adds their own signing key, empties the wallet and pushes the money through fresh accounts to an exchange, often within minutes. Tracing services exist, but they are sold to exchanges and police, so the owner finds out late and has nothing to show anyone. Ripple Guardian is a blockchain forensics framework for the XRP Ledger, and it watches wallets for the people who own them. It tells the owner in plain words when a key changes or funds leave, walks them through recovery, and follows the stolen XRP hop by hop to the exchange and the destination tag that received it: the one number an exchange needs to find the customer. Analysts review what the detectors raise and publish accountable flags that every user can check before sending money.

Everything in the demo runs on XRPL Testnet with real, validated transactions.

<p align="center">
  <img src="artifacts/screenshots/analyst-hop-graph.png" width="860" alt="Hop graph of a traced theft: victim, attacker, two relays, five mules, two exchanges">
  <br><sub>A theft traced on Testnet: 99.99997 XRP from the victim, through two relays and five mules, to two exchange deposit tags.</sub>
</p>

## Contents

- [The hackathon](#the-hackathon)
- [The problem](#the-problem)
- [Our idea](#our-idea)
- [The product](#the-product)
- [How we use the XRP Ledger](#how-we-use-the-xrp-ledger)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [Claims and evidence](#claims-and-evidence)
- [What is simulated](#what-is-simulated)
- [Roadmap](#roadmap)
- [License](#license)
- [Documentation](#documentation)

## The hackathon

**IXH26** is the Italian XRPL Hackathon, held on 20 and 21 November 2026 at the University of Bari Aldo Moro. It is organised by [XRPL Commons](https://www.xrpl-commons.org) and [De Componendis Cifris](https://www.decifris.it/ixh26/) with UBRI, the University of Trento and the University of Bari. Teams of three to eight people had **24 hours of coding**, from Friday 12:00 to Saturday 12:00 CET, then a three-minute pitch with two minutes of questions.

There were three tracks, each with €2,000, €1,200 and €800 for the top three projects:

| Track | Focus |
|---|---|
| 01 · Advanced cryptography | Encryption, zero-knowledge proofs and signatures for blockchain. This year's challenge was proving where a photo comes from. |
| **02 · XRPL applications** | **Our track.** Integrations, apps, DeFi or smart contracts that use the XRP Ledger in a creative way. |
| 03 · Tokenisation on XRPL | Tokens backed by real value, made trustworthy with cryptography. |

### Track 2: XRPL applications

Track 2 is the open track. The organisers' brief:

> No fixed theme, the open track. Build something that meaningfully leverages the XRP Ledger. Whether it's payments, tokenization, DeFi, identity, or something entirely new.

Projects are judged on four criteria. This is how Ripple Guardian answers each one:

| Criterion | Our answer |
|---|---|
| **Idea:** originality and strength of the concept | Theft tracing usually serves exchanges and police. We give it to the person who was robbed, as soon as it happens. |
| **Implementation:** code quality and app experience | A worker that follows the ledger live, a haircut taint tracer, four detectors, a web app for two roles, offline tests for every module and an end-to-end run checked against the ledger. |
| **Demo quality:** clarity and storytelling | A scripted theft on Testnet, followed live from the victim's alert to the exchange deposit tag. |
| **Potential:** real-world impact and room to grow | The trace is exactly the evidence an exchange, or a token issuer using Freeze and Clawback, needs to act. See the [roadmap](#roadmap). |

Rules, criteria and our open questions to the organisers are kept in [docs/CHALLENGE.md](docs/CHALLENGE.md).

## The problem

Stolen XRPL wallets tend to follow the same path. The thief:

1. adds a signing key of their own with `SetRegularKey` or `SignerListSet`, so the owner can't lock them out
2. empties the wallet in one payment to a fresh account
3. splits the money across new accounts, the mules
4. deposits it at an exchange, with a **destination tag** that tells the exchange which customer to credit

```mermaid
flowchart LR
    A([Thief has the seed]) -->|SetRegularKey| V[Victim wallet]
    V -->|"drain · 99.99997 XRP"| D[Fresh account]
    D --> R1[Relay 1]
    D --> R2[Relay 2]
    R1 --> M[Five mules]
    R2 --> M
    M -->|"54.94 XRP · tag 777001"| E1[(Exchange)]
    M -->|"21.98 XRP · tag 4242"| E2[(Exchange B)]
    M -.->|"15.38 XRP kept"| K[One mule]
```

<sub>The theft our demo runs on Testnet. From the key change to the last exchange deposit it took 83 ledgers, about five minutes.</sub>

Every step is public on the ledger, and the destination tag at the end points to one customer account. But the owner usually notices only when the balance is gone, and has no report to hand to the exchange or the police.

## Our idea

**Watch wallets for their owners, not for the exchanges.** Ripple Guardian is one web app with two roles:

- **Wallet owners** add the addresses they want watched. They hear about a theft while it is happening, get a list of what to do, and receive a trace and a report they can hand to an exchange.
- **Analysts** review what the detectors find, trace stolen funds and publish flags. Each flag carries the analyst's name, a category and a reason, and every user can see it.

The first version of the idea had two separate explorers and email notifications. A review on Friday night pushed us to a single app with a permission check, no personal data at all (just a username and a password), and accountable flags. The full story is in [docs/CONTEXT.md](docs/CONTEXT.md), and every decision with its reason is in [docs/DECISIONS.md](docs/DECISIONS.md).

## The product

### For wallet owners

**Sign up without personal data and watch your own wallets.** A username and a password, no email, no phone number. A wallet is watched only after its owner proves they control it, with a one-drop payment that carries a one-time destination tag; until then it shows "Not watched yet" and gets no alerts. Nobody can follow a stranger's wallet through the app. The dashboard shows the state of every wallet in plain words and the latest notifications.

<p align="center">
  <img src="artifacts/screenshots/user-1-wallets.png" width="49%" alt="Owner dashboard: a compromised wallet and the latest notifications">
  <img src="artifacts/screenshots/user-2-wallet.png" width="49%" alt="Wallet page with balance chart and history">
</p>

**Get alerts that say what happened.** The owner is notified when:

- the wallet's signing setup changes: a new regular key, a signer list, the master key disabled, the account deleted
- money leaves above a threshold they choose
- the wallet deals with an address or a transaction an analyst has flagged
- a trace finds where their stolen funds landed

Each alert type can be switched off per wallet.

**Recover after a theft.** A robbed owner gets four steps: lock the wallet, move what is left, find the money, report it. One click asks an analyst for a trace. When it finishes, the owner sees which exchange received the funds, under which destination tag and how much, and downloads a [PDF incident report](artifacts/screenshots/incident-report.pdf) with every transaction link and a SHA-256 fingerprint of the evidence.

<p align="center">
  <img src="artifacts/screenshots/user-3-recover.png" width="49%" alt="Four-step recovery screen">
  <img src="artifacts/screenshots/user-3b-notifications.png" width="49%" alt="Notifications: key changed, XRP sent, stolen funds located">
</p>

**Check an address before paying.** Any user can look up an address and see whether an analyst flagged it, by whom and why.

<p align="center">
  <img src="artifacts/screenshots/user-4-check-address.png" width="70%" alt="Address check showing an analyst flag">
</p>

### For analysts

**An overview and a findings queue.** Four detectors run on the history of watched wallets:

| Detector | Looks for | Live on Testnet |
|---|---|---|
| Possible takeover | A key change followed by a drain to new destinations | yes |
| Funds funnel | Several accounts forwarding to the same exchange destination tag | yes |
| Wash trading | Heavy order-book trading inside a small group of wallets that leaves their holdings almost unchanged | built and tested, needs DEX data |
| Liquidity withdrawal | New buyers followed by a sudden AMM withdrawal | built and tested, needs AMM data |

Analysts can tune every threshold on the Detection settings page, and the worker picks up the new values on its next run.

<p align="center">
  <img src="artifacts/screenshots/analyst-1-overview.png" width="49%" alt="Analyst overview: exchange exposure, live ledger, findings">
  <img src="artifacts/screenshots/analyst-2-findings.png" width="49%" alt="Findings queue with takeover and funnel findings">
</p>

**Taint tracing.** From a takeover finding or a robbed wallet, the analyst starts a trace. The result is an animated hop graph: each account shows the tainted amount it received and its share of the theft, links get thicker as more value flows through them, and hovering an account highlights its money path. Below the graph, every endpoint and every tainted transfer is listed with its transaction.

<p align="center">
  <img src="artifacts/screenshots/analyst-hop-graph-hover.png" width="49%" alt="Hovering a pass-through account highlights its money path">
  <img src="artifacts/screenshots/analyst-3-trace.png" width="49%" alt="Trace page with endpoints and tainted transfers">
</p>

**Accountable flags.** Flags carry the analyst's name, a category and a reason, can be revoked, and are visible to every user.

<details>
<summary>Detection settings screenshot</summary>
<br>
<p align="center">
  <img src="artifacts/screenshots/analyst-detection-settings.png" width="80%" alt="Detection settings for the four detectors">
</p>
</details>

## How we use the XRP Ledger

| XRPL feature | What Ripple Guardian does with it |
|---|---|
| `subscribe` over WebSocket | Follows every watched account live |
| `account_tx` over JSON-RPC | Catches up on anything the stream missed, backfills new wallets and walks the hops of a trace |
| `SetRegularKey`, `SignerListSet`, `AccountSet` (disable master key), `AccountDelete` | Read as security events: the first sign of a takeover |
| `Payment`, `CheckCash`, `EscrowFinish`, `PaymentChannelClaim`, `AccountDelete` | Every way XRP can leave an account, so the trace can't be dodged by moving funds without a plain payment |
| `delivered_amount` in transaction metadata | The only amount we trust, so a partial payment can't fake a theft or a trace |
| Destination tags | Where a trace ends: the customer account at the exchange |
| One-drop `Payment` with a one-time destination tag | Proof that a user controls a wallet, required before it is watched |
| `tx` lookup by hash | Find any validated transaction on Testnet or Mainnet from the app |

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

> [!TIP]
> On WSL, Python DNS lookups can stall on IPv6 and make every Testnet call time out. Prefix the command with `RES_OPTIONS="timeout:1 attempts:1"` if that happens.

## Claims and evidence

| Claim | Evidence |
|---|---|
| A real theft on Testnet is detected, traced and explained to the owner | [docs/E2E.md](docs/E2E.md), `artifacts/tx_log.jsonl`, `artifacts/screenshots/` |
| A laundering tree (2 relays, 5 mules, 2 exchanges) is traced over 4 hops: 12 tainted transfers, 55% located at Exchange tag 777001, 22% at Exchange B tag 4242, 15% held by a mule | run 2 in [docs/E2E.md](docs/E2E.md); rekey [F60AA3C4…](https://testnet.xrpl.org/transactions/F60AA3C4C14EE016BBD26D5BEF208146AAA9545640D526318E897D12CEE1FF10), drain [5824D3C4…](https://testnet.xrpl.org/transactions/5824D3C46D3B223031BFFD93364BDD6A102AC3A91C9EE80C029EFB749430AECB), deposits [7758D5E4…](https://testnet.xrpl.org/transactions/7758D5E4C3C8BE47CA4C51167183E0C3380CB448BACF775A42741D432C00C29C), [2E42BD03…](https://testnet.xrpl.org/transactions/2E42BD03C6417115DF303F0BD9F8E95B56DD33B5CA326459352FF697752C5F72), [00C94FE3…](https://testnet.xrpl.org/transactions/00C94FE3890E8896696F447A26A91841352B48DC6C1190A5DF63E61B159FF566), [F995F492…](https://testnet.xrpl.org/transactions/F995F492813FE51D07A89B95D1A3FEA380995BDF34ED082FAE9BBFF9C71D5FC0) |
| The trace matches the ledger: 7 of 7 edges agree with `tx` (sender, receiver, tag, delivered amount) | run 1 in [docs/E2E.md](docs/E2E.md), drain [9C004106…](https://testnet.xrpl.org/transactions/9C004106BB908901B1B328AD82272EA253D1EB2C116F1146553D1018A7EB4E3F) |
| Amounts come from `delivered_amount`, so partial payments cannot inflate them | `tests/ledger/test_ledger_normalize.py::test_partial_payment_reports_delivered_not_requested_amount` |
| Haircut taint follows ledger order, dilutes with clean funds and stops at 1% or the hop limit | `tests/core/test_taint.py` |
| Owners hear about key changes, outgoing payments and flagged counterparties, within their own settings | `tests/core/test_alerts.py`, `tests/flows/test_flows.py` |
| A missed WebSocket message is caught up by polling, without alerting on old history | `tests/flows/test_flows.py::test_polling_backfills_silently_then_catches_up_with_alerts` |
| A robbed owner gets a 4-step recovery screen, can ask for a trace, and downloads a PDF report with every tx link and a SHA-256 fingerprint | `tests/flows/test_report.py`, `tests/app/test_web.py::test_owner_can_request_a_trace_of_their_theft`, `artifacts/screenshots/incident-report.pdf` |
| Users can't open analyst pages; analyst flags are visible to users | `tests/app/test_web.py`, `scripts/e2e_browser.py` run in [docs/E2E.md](docs/E2E.md) |
| Takeover and funnel detectors fire on live Testnet data | findings in [docs/E2E.md](docs/E2E.md); rules in `tests/core/test_detection.py` |
| Testnet is the default. Mainnet is opt-in with `XRPL_NETWORK=mainnet`, needs its own database and never submits a transaction. Any validated transaction can be looked up by hash on either network, from the Find transaction page | `tests/test_config.py`, `tests/app/test_transaction_api.py`, `tests/store/test_network_store.py` |
| A normal user's wallet is monitored only after its owner proves control with a one-drop payment that carries a one-time destination tag (valid 15 minutes). Until then it is stored, no alerts are sent and the worker skips it. Analysts are exempt | `tests/app/test_verification.py`, `tests/app/test_frontend_pages.py`, `tests/flows/test_flows.py::test_unverified_wallets_are_not_monitored_until_the_owner_proves_control` |
| Amounts are never floats and seeds can't be committed | `tests/test_contracts.py`, `tests/test_secret_scan.py` |
| Analysts adjust the four detector rules on the Detection settings page or through the API, with version checks between analysts, and the worker reads saved thresholds on its next run | `tests/app/test_detector_settings_api.py`, `tests/app/test_frontend_pages.py`, [frontend API handoff](docs/FRONTEND-BACKEND-HANDOFF.md) |

<details>
<summary>Run 2 transactions, as the ledger records them</summary>
<br>

Looked up again with `tx` on a public Testnet node on 21 November 2026. All six are validated with `tesSUCCESS`.

| Step | Type | Ledger | Delivered | Destination tag |
|---|---|---|---|---|
| [Rekey](https://testnet.xrpl.org/transactions/F60AA3C4C14EE016BBD26D5BEF208146AAA9545640D526318E897D12CEE1FF10) | `SetRegularKey` | 22495208 | | |
| [Drain](https://testnet.xrpl.org/transactions/5824D3C46D3B223031BFFD93364BDD6A102AC3A91C9EE80C029EFB749430AECB) | `Payment` | 22495215 | 99.99997 XRP | |
| [Deposit](https://testnet.xrpl.org/transactions/7758D5E4C3C8BE47CA4C51167183E0C3380CB448BACF775A42741D432C00C29C) | `Payment` | 22495271 | 25.107992 XRP | 777001 |
| [Deposit](https://testnet.xrpl.org/transactions/2E42BD03C6417115DF303F0BD9F8E95B56DD33B5CA326459352FF697752C5F72) | `Payment` | 22495277 | 19.283994 XRP | 777001 |
| [Deposit](https://testnet.xrpl.org/transactions/00C94FE3890E8896696F447A26A91841352B48DC6C1190A5DF63E61B159FF566) | `Payment` | 22495284 | 10.547996 XRP | 777001 |
| [Deposit](https://testnet.xrpl.org/transactions/F995F492813FE51D07A89B95D1A3FEA380995BDF34ED082FAE9BBFF9C71D5FC0) | `Payment` | 22495291 | 21.975993 XRP | 4242 |

The three deposits under tag 777001 add up to 54.939982 XRP, the 54.94 XRP the trace reports.
</details>

## What is simulated

- Exchange and Exchange B are Testnet wallets we control, shown as "SIMULATED" in the app. Real exchanges would be added as labels with `ixh26 label`.
- The theft is scripted by `scripts/demo.py`. Its transactions are real and validated on Testnet.
- `make smoke` and the offline tests use synthetic addresses and hashes, marked `SIMULATED` in the code. They never appear in the app or in the evidence.
- The wash trading and liquidity drop detectors are built and tested, but the ledger reader does not yet extract DEX fills or AMM withdrawals, so they get no live data.

## Roadmap

- Ask the issuer to freeze or claw back stolen tokens (trust line freeze, Clawback), using the trace as evidence.
- Read DEX fills and AMM withdrawals, so all four detectors run live and taint can follow funds across currencies.
- Opt-in push or email delivery.
- Mainnet in the web app. The backend can watch and trace on Mainnet, read-only, but the demo and all evidence stay on Testnet until the evidence format has been reviewed with an exchange.

## License

Ripple Guardian is released under the [Apache License 2.0](LICENSE). You can use, modify and share it, including commercially, as long as you keep the [NOTICE](NOTICE) file and credit **Cyber Guys** as the original authors.

The names "Ripple Guardian" and "Cyber Guys" and the project logo are not covered by the licence. Third-party libraries and assets keep their own licences, listed in [THIRD_PARTY.md](THIRD_PARTY.md).

## Documentation

| File | For | What it covers |
|---|---|---|
| [docs/CHALLENGE.md](docs/CHALLENGE.md) | everyone | hackathon rules, track, judging criteria |
| [docs/CONTEXT.md](docs/CONTEXT.md) | newcomers, human or agent | the idea, how it changed during the night, glossary |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | developers | modules, data flow, the code behind each step |
| [docs/DESIGN.md](docs/DESIGN.md) | judges, reviewers | threat model and known limits |
| [docs/E2E.md](docs/E2E.md) | judges | the Testnet runs, checked against the ledger and in a browser |
| [docs/DECISIONS.md](docs/DECISIONS.md) | team | every decision with its reason |
| [docs/trailer/README.md](docs/trailer/README.md) | everyone | the trailer: rendered videos, captures, music and how to rebuild them |
| [docs/SUBMISSION.md](docs/SUBMISSION.md) | organisers | submission text, third-party summary, AI disclosure |
| [CLAUDE.md](CLAUDE.md) | AI agents | the rules every agent working on this repo follows |
| [THIRD_PARTY.md](THIRD_PARTY.md) | everyone | every library and asset with its licence |
