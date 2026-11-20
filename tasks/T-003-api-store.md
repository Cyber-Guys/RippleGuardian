---
id: T-003
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-003-api-store
depends_on: [T-000]
scope: [src/ixh26/store/, src/ixh26/app/, tests/store/, tests/app/]
contracts_used: [Transfer, TaintEdge, TraceResult, Alert]
policy: "1.0"
---
## Objective
FastAPI exposes users (JWT), watched wallets, alerts and trace endpoints, persisted in Postgres.
## Acceptance criteria
- [ ] Register/login with JWT; wallets CRUD scoped to user
- [ ] POST /traces starts a trace, GET returns graph
- [ ] Tests with sqlite/in-memory backend
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
## Evidence
