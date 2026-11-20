---
id: T-002
objective: O-1
status: todo
owner: tommaso/a1
branch: t/T-002-taint-engine
depends_on: [T-000]
scope: [src/ixh26/core/, tests/core/]
contracts_used: [Transfer, TaintEdge, TraceResult]
policy: "1.0"
---
## Objective
`core/taint` computes haircut taint propagation over a transfer graph with temporal order, 1% threshold and max hops.
## Acceptance criteria
- [ ] Haircut proportional to balance, only outflows after tainted inflow count
- [ ] Stops below 1% / min amount and beyond max hops
- [ ] Deterministic offline tests (split, merge, cycle, exchange sink)
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
## Evidence
