---
id: T-004
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-004-monitor-worker
depends_on: [T-001, T-002, T-003]
scope: [src/ixh26/flows/, tests/flows/, src/ixh26/cli.py]
contracts_used: [Transfer, SecurityEvent, Alert, TraceResult]
policy: "1.0"
---
## Objective
A worker watches all registered wallets (WebSocket subscribe + periodic polling), stores events, raises alerts and runs traces.
## Acceptance criteria
- [ ] Outgoing payment / SetRegularKey on a watched wallet creates an Alert
- [ ] Trace job populates the graph in the DB
- [ ] Polling catches up after a WebSocket disconnect
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
## Evidence
