---
id: T-003
objective: O-1
status: review
owner: nico/claude
branch: t/T-003-api-store
depends_on: [T-000]
scope: [src/ixh26/store/, src/ixh26/app/, tests/store/, tests/app/, tests/conftest.py]
contracts_used: [Transfer, TaintEdge, TraceResult, Alert]
policy: "1.0"
---
## Objective
FastAPI exposes users (JWT), watched wallets, alerts and trace endpoints, persisted in Postgres.
## Acceptance criteria
- [x] Register/login with JWT; wallets CRUD scoped to user
- [x] POST /traces starts a trace, GET returns graph
- [x] Tests with sqlite/in-memory backend
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
- 00:20 nico/claude: store/ (SQLAlchemy, sqlite or Postgres, create_all, no migrations), app/auth.py (argon2 + JWT cookie/bearer, roles user|analyst), app/api.py JSON API, app/main.py create_app (mounts app/web.py if present). Traces are queued as pending rows; the worker (T-004) runs them. Local run without docker: DATABASE_URL=sqlite:///data/guardian.db.
## Evidence
- tests/store/test_store.py (idempotent activity, per-user alerts, findings/flags/traces)
- tests/app/test_api.py (register/login, wallet CRUD + thresholds, 403 for users on analyst endpoints, flags visible to users, trace queued)
