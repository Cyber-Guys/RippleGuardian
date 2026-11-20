---
id: T-002
objective: O-1
status: review
owner: nico/claude
branch: t/T-002-taint-engine
depends_on: [T-000]
scope: [src/ixh26/core/, tests/core/]
contracts_used: [Transfer, TaintEdge, TraceResult]
policy: "1.0"
---
## Objective
`core/taint` computes haircut taint propagation over a transfer graph with temporal order, 1% threshold and max hops.
## Acceptance criteria
- [x] Haircut proportional to balance, only outflows after tainted inflow count
- [x] Stops below 1% / min amount and beyond max hops
- [x] Deterministic offline tests (split, merge, cycle, exchange sink)
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
- 23:55 nico/claude: core/taint.py pure haircut. Unknown opening balances default to 0 and oversized outflows draw on untainted funds; flows/ should pass opening balances at start_ledger. Labelled accounts absorb taint (sinks per destination tag). Same-asset only; DEX cross-asset is roadmap.
## Evidence
- tests/core/test_taint.py: split + exchange sink by tag, haircut dilution and temporal order, merge + cycle conservation, threshold + max hops
