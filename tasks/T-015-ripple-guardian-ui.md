---
id: T-015
objective: O-1
status: done
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
- [x] Name in one constant; original logo (no Ripple/XRP marks)
- [x] Notifications: short title, details expand on hover/focus/click
- [x] Recovery screen per wallet with steps, trace result if any, PDF download
- [x] PDF incident report with timeline, tx links, destination tag, evidence fingerprint
- [x] Analyst: animated hop graph (no JS), live feed and exchange exposure
- [x] make check, make smoke, browser check on both roles
## Out of scope
Mainnet, Clawback/Freeze.
## Log
- 02:15 nico/claude: policy 1.0 acknowledged. nico's instruction. Note: "Ripple" is a Ripple Labs trademark; flagged to nico, name kept in one constant.
- 10:02 nico/claude: rename (BRAND constant), original ripple-shield mark (static/logo.svg), ink sidebar and alarm hero with pulsing ripples, shorter copy, expandable notifications (hover/focus, CSS grid-rows), recovery page (timeline, 4 steps with progress, owner can queue a trace), PDF incident report (fpdf2) with tx links and SHA-256 fingerprint, analyst overview with animated hop graph (SVG draw-in + animateMotion particles, Replay), exchange exposure and live ledger feed. Work done after the 06:00 feature freeze on nico's explicit instruction. Merged to master with nico's OK.
## Evidence
- make check 75 passed; tests/flows/test_report.py; tests/app/test_web.py (recovery, PDF, trace request, live feed, flow replay)
- scripts/e2e_browser.py on the docker stack: both roles, PDF download, 0 console errors; artifacts/screenshots/ and incident-report.pdf
- 10:10 nico/claude: hop graph redone as a node-link graph (circles per account, curved arrows per transfer, value particles), on nico's request.
- 10:42 nico/claude: T-017 light white/grey/celeste palette (inspired by the dashboard-shell prompt, no React), node depth, hover path highlight, beacons on the next action, multi-hop demo (2 relays, 5 mules, 2 exchanges). After the 10:30 merge freeze, on nico's explicit instruction.
