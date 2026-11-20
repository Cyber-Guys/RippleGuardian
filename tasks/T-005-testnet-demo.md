---
id: T-005
objective: O-1
status: todo
owner: tommaso/a1
branch: t/T-005-testnet-demo
depends_on: [T-004]
scope: [scripts/, artifacts/, tests/scripts/]
contracts_used: []
policy: "1.0"
---
## Objective
`make demo` runs a scripted theft on Testnet (victim -> attacker split -> mule hops -> exchange + tag) and shows the backend tracing it.
## Acceptance criteria
- [ ] Idempotent wallet setup via faucet, seeds only in .env
- [ ] Every tx in artifacts/tx_log.jsonl with explorer link
- [ ] Trace output reaches the exchange address + destination tag
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
## Evidence
