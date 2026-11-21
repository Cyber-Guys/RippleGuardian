---
id: T-013
objective: O-1
status: done
owner: nico/claude
branch: t/T-013-ui-dashboard
depends_on: [T-012]
scope: [src/ixh26/store/repo.py, src/ixh26/app/templates/, src/ixh26/app/static/, src/ixh26/app/charts.py, src/ixh26/app/views/, tests/app/, THIRD_PARTY.md]
contracts_used: []
policy: "1.0"
---
## Objective
A clean liquid-glass UI with dashboards and SVG charts that make wallet state and the funds flow obvious.
## Acceptance criteria
- [x] user overview: plain-language status, balance flow chart, alert timeline
- [x] analyst dashboard: KPIs, findings by detector, funds-flow graph (SVG, server-rendered)
- [x] liquid-glass surfaces + motion, reduced-motion respected
- [x] tests for chart helpers and pages
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
- 01:55 nico/claude: direction (unslop): calm, exact, vigilant; glass instrument panel on silver paper; moments = funds-flow graph + balance line; signature = live ledger pulse (worker cursor). Liquid glass (backdrop blur + edge highlight) on sidebar, status heroes, auth card only. One easing curve cubic-bezier(.32,.72,0,1), one entrance, chart draw-in, reduced-motion respected. Charts are server-rendered SVG (app/charts.py), accent validated with the dataviz palette script. MockFlow MCP (liquid-glass skill) not available: used its visual spec only. 21st.dev components are React: used as reference only. Added store.repo.latest_ledger. Merged to master with nico's OK.
## Evidence
- tests/app/test_web.py: flow nodes/bands, balance line, analyst overview, named dashboard headline
- Playwright run (form login as user and analyst, 0 console errors), screenshots reviewed
