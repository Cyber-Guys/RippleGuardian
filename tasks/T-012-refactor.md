---
id: T-012
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-012-refactor
depends_on: [T-005, T-008]
scope: [src/ixh26/flows/, src/ixh26/app/api.py, src/ixh26/app/auth.py, src/ixh26/app/web.py, src/ixh26/app/views/, src/ixh26/ledger/, src/ixh26/core/taint.py, tests/]
contracts_used: []
policy: "1.0"
---
## Objective
Each module and function does one job and reads top-down; behaviour unchanged.
## Acceptance criteria
- [ ] web.py split into per-role routers and view models
- [ ] alert rules in monitor.py are small pure functions
- [ ] make check and make smoke green, no behaviour change
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
## Evidence
