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

## D-005 · One app, two roles, no personal data, in-app notifications
- Date: 2026-11-20 23:15 CET · Decided by: nico (drafted by nico/claude, pending approval)
- Status: accepted
- Decision: A single web app with a `user` and an `analyst` role replaces the "two explorers" idea. Users see only their watched wallets (history, statement, notification settings) and the accounts/txs flagged by analysts. Analysts see detector findings, run haircut traces and flag accounts/txs. Accounts are pseudonymous (username + password, no email). Notifications are in-app only and fire on (a) activity on a watched wallet (outgoing payment above a per-wallet threshold, signing-key change) and (b) contact with a flagged account. Wallets are watch-only (public data); proof of ownership is roadmap.
- Why: Execution (one app to build and demo), Impact (detection and flags stay with accountable analysts), no personal data on our side.
- Alternatives considered: two explorers; email notifications (dropped, personal data); ownership proof via a tagged micro-payment (roadmap).
- Consequences: T-008, T-009; AlertKind.FLAGGED_COUNTERPARTY.

## D-006 · Web front-end: Jinja2 + HTMX inside FastAPI
- Date: 2026-11-20 23:15 CET · Decided by: nico
- Status: accepted
- Decision: Server-rendered Jinja2 templates served by the same FastAPI app; HTMX (vendored static file) for live fragments. One CSS file with design tokens; animation hooks only, animations later.
- Why: Python-first policy (no JS we write), one container, signing stays server-side.
- Alternatives considered: NiceGUI, Streamlit, a JS SPA (needs the JS exception).
- Consequences: Jinja2 + python-multipart dependencies; HTMX listed in THIRD_PARTY.md. Live notifications use HTMX polling of the DB; Redis pub/sub is not used for now.
