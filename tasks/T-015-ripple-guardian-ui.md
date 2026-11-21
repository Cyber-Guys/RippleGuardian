---
id: T-015
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-015-ripple-guardian-ui
depends_on: [T-013, T-014]
scope: [src/ixh26/app/, src/ixh26/flows/report.py, src/ixh26/store/repo.py, tests/app/, tests/flows/, pyproject.toml, uv.lock, THIRD_PARTY.md, README.md, docs/]
contracts_used: [Alert, TraceResult]
policy: "1.0"
---
## Objective
Ripple Guardian: a distinctive, high-contrast UI with an original logo, short copy, expandable notifications, a step-by-step recovery screen, a downloadable incident report (PDF) and an animated hop graph for analysts.
## Acceptance criteria
- [ ] Name in one constant; original logo (no Ripple/XRP marks)
- [ ] Notifications: short title, details expand on hover/focus/click
- [ ] Recovery screen per wallet with steps, trace result if any, PDF download
- [ ] PDF incident report with timeline, tx links, destination tag, evidence fingerprint
- [ ] Analyst: animated hop graph (no JS), live feed and exchange exposure
- [ ] make check, make smoke, browser check on both roles
## Out of scope
Mainnet, Clawback/Freeze.
## Log
- 02:15 nico/claude: policy 1.0 acknowledged. nico's instruction. Note: "Ripple" is a Ripple Labs trademark; flagged to nico, name kept in one constant.
## Evidence
