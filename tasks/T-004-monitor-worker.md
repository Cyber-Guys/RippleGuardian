---
id: T-004
objective: O-1
status: todo
owner: tommaso/a1
branch: t/T-004-monitor-worker
depends_on: [T-001, T-002, T-003]
scope: [src/ixh26/flows/, tests/flows/]
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
## Evidence
