# IXH26 · XRPL Wallet Guardian

> **Status: skeleton (T-000) and offline detection backend (T-006).** Only the items in the
> claim → evidence table below are built.

## Pitch
When an XRPL wallet is compromised, the attacker typically rotates keys (`SetRegularKey`,
`SignerListSet`), drains the balance, splits it across throw-away wallets and walks it towards
an exchange. Enterprise tracers (Elliptic, Chainalysis, TRM) serve exchanges and law enforcement
*after* the fact. Wallet Guardian is an open-source, XRPL-native service for the individual holder:
it watches your wallet, alerts on the first suspicious move, and traces stolen funds hop by hop
with a documented **haircut taint** model (1% threshold) until they reach an exchange
address + destination tag or a token issuer that can freeze / claw back.

## Architecture
```
            ┌────────────── docker compose ───────────────┐
 user ──JWT─▶ api (FastAPI)          worker (monitor + tracer)│
            │   │                     │  ▲ subscribe (WS)     │
            │   ▼                     ▼  │ account_tx (poll)  │──▶ XRPL Testnet
            │ Postgres ◀── store ──▶ Redis (jobs, pub/sub)    │
            └─────────────────────────────────────────────────┘
 src/ixh26: core/ (detection and taint, no xrpl) · ledger/ (all XRPL) · store/ (DB) · flows/ · app/
```

## Quickstart
```bash
make setup          # uv sync + .env from .env.example (set JWT_SECRET)
make check          # lint, format, offline tests, secret scan
make smoke          # headless demo path
make up             # docker compose: api + worker + postgres + redis
make demo           # scripted theft on Testnet + trace (T-005, not built yet)
```

## Claim → evidence
| Claim | Evidence |
|---|---|
| Mainnet is refused by configuration | `tests/test_config.py::test_mainnet_and_unknown_networks_are_refused` |
| Amounts are never floats; XRP is integer drops | `tests/test_contracts.py` |
| CI fails on committed XRPL seeds / private keys | `tests/test_secret_scan.py`, `make check` |
| Dockerized stack | `docker compose build` (T-000 Evidence) |
| Four backend detectors return rule measurements and transaction evidence | `tests/core/test_detection.py` |

## What is SIMULATED
T-006's offline tests use synthetic activity and identifiers marked `SIMULATED`. The demo theft
(T-005) will be a *scripted* scenario on Testnet with real tx hashes.

## Roadmap
Monitoring + alerts (T-004), haircut tracer (T-002), API + auth (T-003), Testnet demo (T-005).
Roadmap includes live detection ingestion and alert delivery, model training, paid subscriptions,
FIFO/poison models, and cross-chain bridge following.

### Detection backend

Call `ixh26.core.detection.detect(DetectionBatch(...))` with normalized, validated activity and
enough earlier history for the rule windows. The offline entry point returns findings with a
triggering transaction, evidence hashes, and named measurements. Ratios are `Decimal`; XRP amounts
and quotes are in drops. `DetectionSettings` exposes the starting thresholds for replay.

- **Funds funnel.** Three distinct wallets forward at least 80% of recently received funds to a
  common destination in 30 minutes. Routes include the destination tag and exact asset issuer.
  Matched inflow is an upper bound based on observable deposits and debits.
- **Possible wash trading.** At least six executed order-book fills in 30 minutes form a recurring
  group of at most six wallets, with at least 50% of observed market volume and at most 15% net
  movement relative to gross volume. Provide one record per executed fill and its two accounts.
- **Pool liquidity drop.** At least three buyers cross to a positive token balance within the hour
  before a withdrawal removes at least half the XRP from a pool that held at least 10 XRP. The
  estimated before/after sale uses that AMM's reserves and trading fee. Issuer transfer fees and
  alternative trading routes are outside the estimate.
- **Possible takeover.** A signing change is followed within 15 minutes by same-asset outflows to
  new destinations totaling at least 70% of the starting balance for that asset. Supply the
  signing transaction's position, the pre-outflow balance, and known prior destinations.

Findings indicate activity for review. Exchanges, market makers, liquidity migrations, and
authorized key rotations can produce similar observations.

## Team
See `docs/SUBMISSION.md`.
