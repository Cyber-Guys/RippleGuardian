# IXH26 · XRPL Wallet Guardian

> **Status: skeleton (T-000).** Only the items in the claim → evidence table below are built.

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
 src/ixh26: core/ (taint engine, no xrpl) · ledger/ (all XRPL) · store/ (DB) · flows/ · app/
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

## What is SIMULATED
Nothing yet. The demo theft (T-005) will be a *scripted* scenario on Testnet with real tx hashes.

## Roadmap
Monitoring + alerts (T-004), haircut tracer (T-002), API + auth (T-003), Testnet demo (T-005).
Not planned for the hackathon: detection system, paid subscriptions, FIFO/poison models,
cross-chain bridge following.

## Team
See `docs/SUBMISSION.md`.
