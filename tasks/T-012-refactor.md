---
id: T-012
objective: O-1
status: done
owner: nico/claude
branch: t/T-012-refactor
depends_on: [T-005, T-008]
scope: [src/ixh26/core/alerts.py, src/ixh26/flows/, src/ixh26/app/api.py, src/ixh26/app/auth.py, src/ixh26/app/web.py, src/ixh26/app/views/, src/ixh26/ledger/, src/ixh26/core/taint.py, tests/]
contracts_used: []
policy: "1.0"
---
## Objective
Each module and function does one job and reads top-down; behaviour unchanged.
## Acceptance criteria
- [x] web.py split into per-role routers and view models
- [x] alert rules in monitor.py are small pure functions
- [x] make check and make smoke green, no behaviour change
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
- 01:27 nico/claude: alert rules moved to pure core/alerts.py; monitor.py = save -> deliver -> detect with wants()/detection_batch(); trace.py split into job (trace.py) and JSON report (trace_report.py, now also raw taint_value numbers); ledger normalize uses one extractor per tx type (EXTRACTORS table); web.py split into app/views/{common,models,auth_pages,user_pages,flag_pages,analyst_pages}.py. Merged to master with nico's OK.
## Evidence
- make check 72 passed (new tests/core/test_alerts.py), make smoke ok
