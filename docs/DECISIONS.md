# Decision log

Append-only. Humans make decisions; agents may draft an entry, but it counts only once a human has approved it and it is merged.
To reverse a decision, add a new entry that supersedes it. Don't edit old entries.

**Format**
```
## D-00n · <short title>
- Date: YYYY-MM-DD HH:MM CET · Decided by: <human(s)>
- Status: accepted | superseded by D-00m
- Decision: <one or two sentences>
- Why: <the reason, ideally tied to a judging criterion or a contest rule>
- Alternatives considered: <briefly>
- Consequences: <what changes for tasks, scope, the policy>
```

---

## D-001 · Project direction: XRPL Wallet Guardian
- Date: 2026-11-20 21:00 CET · Decided by: tommaso
- Status: accepted
- Decision: A web service where a user registers their XRPL wallet(s); it monitors them, alerts on suspicious activity and, after a theft, traces the stolen funds with a haircut taint model (stop below 1% of the stolen amount or after max hops) until exchanges (address + destination tag) or token issuers. A detection system and paid subscriptions are planned but **not** built now.
- Why: Impact (individual holders are not served by enterprise tracers), Innovation (open-source, XRPL-native: delivered_amount, IOU/DEX, Freeze/Clawback, destination tags), Execution (real Testnet tx graph).
- Alternatives considered: federated learning with XRPL registry/payouts (earlier brainstorm); a pure post-theft forensic tool.
- Consequences: O-1 and T-000..T-005. Testnet only: the demo theft is scripted on Testnet with real tx hashes.

## D-002 · UI framework (Python)
- Date: 2026-11-20 21:00 CET · Decided by: tommaso
- Status: accepted
- Decision: Backend API in FastAPI. The webapp front-end framework is decided in a later entry.
- Why: The backend is the first deliverable; FastAPI gives typed JSON API + OpenAPI docs usable as a demo UI meanwhile.
- Alternatives considered: Streamlit, NiceGUI.
- Consequences: `app/` holds the FastAPI app.

## D-003 · Backend stack
- Date: 2026-11-20 21:00 CET · Decided by: tommaso
- Status: accepted
- Decision: FastAPI + Postgres (SQLAlchemy/psycopg) + Redis, run with docker compose (api, worker, db, redis). xrpl-py; tracks XRP **and** IOU tokens; wallets watched by WebSocket `subscribe` plus periodic `account_tx` polling as catch-up; users authenticated with JWT (argon2 password hashes).
- Why: Execution (real multi-service backend, resilient monitoring), user requirement "must be dockerized".
- Alternatives considered: SQLite single process; polling only; no auth.
- Consequences: dependencies added in T-000; Postgres/Redis only via `store/`.

## D-004 · Module layout
- Date: 2026-11-20 21:00 CET · Decided by: tommaso
- Status: accepted
- Decision: Keep `core/ ledger/ flows/ app/` and add `store/` (persistence: Postgres + Redis). `store/` imports neither `ledger/` nor `xrpl`; `app/` uses `flows/` and `store/` read models; `core/taint` is pure (no DB, no xrpl).
- Why: CLAUDE.md §4 module boundaries; lets T-001/T-002/T-003 run in parallel.
- Alternatives considered: persistence inside `flows/`.
- Consequences: shared types in `contracts.py` (Transfer, SecurityEvent, TraceParams, TraceResult, Alert, TxResult, LedgerReader/LedgerStream protocols).
