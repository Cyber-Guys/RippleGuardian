---
id: T-013
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-013-ui-dashboard
depends_on: [T-012]
scope: [src/ixh26/app/templates/, src/ixh26/app/static/, src/ixh26/app/charts.py, src/ixh26/app/views/, tests/app/, THIRD_PARTY.md]
contracts_used: []
policy: "1.0"
---
## Objective
A clean liquid-glass UI with dashboards and SVG charts that make wallet state and the funds flow obvious.
## Acceptance criteria
- [ ] user overview: plain-language status, balance flow chart, alert timeline
- [ ] analyst dashboard: KPIs, findings by detector, funds-flow graph (SVG, server-rendered)
- [ ] liquid-glass surfaces + motion, reduced-motion respected
- [ ] tests for chart helpers and pages
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
## Evidence
