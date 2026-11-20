---
id: T-004
objective: O-1
status: review
owner: nico/claude
branch: t/T-004-monitor-worker
depends_on: [T-001, T-002, T-003, T-006]
scope: [src/ixh26/flows/, tests/flows/, src/ixh26/cli.py]
contracts_used: [Transfer, SecurityEvent, Alert, TraceResult]
policy: "1.0"
---
## Objective
A worker watches all registered wallets (WebSocket subscribe + periodic polling), stores events, raises alerts and runs traces.
## Acceptance criteria
- [x] Outgoing payment / SetRegularKey on a watched wallet creates an Alert
- [x] Trace job populates the graph in the DB
- [x] Polling catches up after a WebSocket disconnect
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
- 00:10 nico/claude: merged origin/t/T-006-fraud-detectors (in review, daniele) into this branch: T-004 needs its detect(). flows/monitor.py (store + alerts: outgoing above threshold, signing change, flagged counterparty; detectors over stored history), flows/trace.py (hop-by-hop fetch, opening balances, haircut, JSON result, TAINT_AT_EXCHANGE alert to victim), flows/worker.py (stream + poll + trace jobs), flows/smoke.py (SIMULATED offline demo path for make smoke), cli create-user/label. Gotcha: wash-trading/liquidity detectors get no live input (no DEX/AMM normalisation yet).
## Evidence
- tests/flows/test_flows.py: demo path, flagged counterparty + thresholds, notify toggle, silent backfill then catch-up after disconnect, trace job done/failed, CLI
- make smoke: 6/6 checks ok
