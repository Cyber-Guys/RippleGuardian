---
id: T-018
objective: O-1
status: review
owner: nico/claude
branch: t/T-018-integrate-ui
depends_on: [T-015, T-016, T-017]
scope: [src/ixh26/app/static/app.css, src/ixh26/app/templates/, src/ixh26/app/charts.py, src/ixh26/app/views/, tests/app/test_web.py, scripts/e2e_browser.py, README.md, docs/, tasks/]
contracts_used: []
policy: "1.1"
---
## Objective
Integrate T-016 (network switch) and T-017 (wallet verification) and refine the UI: grey layered palette, full wallet address, "What to do" wording, equal-height dashboard grid, a calmer hop graph with node details on hover or click.
## Acceptance criteria
- [x] T-016 and T-017 merged on top of the rewritten master; make check and make smoke green
- [x] Palette uses layered greys; muted text keeps at least 4.5:1 contrast
- [x] Wallet card and alarm show the full address with a copy button; "Start recovery" becomes "What to do"
- [x] Dashboards have equal-height rows; user home has a KPI row
- [x] Hop graph labels only victim, exchanges and funds kept; node details appear on hover or focus
## Out of scope
UI for wallet verification (backend only for now), mainnet UI switch.
## Log
- 11:00 nico/claude: policy 1.1 acknowledged. master history was rewritten on origin (same trees, new hashes, no AI trailers); local master realigned, old one kept as backup/master-before-rewrite. T-016 and T-017 merged without conflicts (95 tests). Note: T-016 enables Mainnet reads while CLAUDE.md section 5 still says Mainnet is forbidden: daniele requested it, nico confirmed; default stays Testnet. Needs a human DECISIONS entry or a policy update.
- 11:10 nico/claude: palette in layered greys (page #d9e0e8, cards #f6f8fa, insets #cfd8e2; muted text #566274 keeps 4.6:1 or more), full wallet address on cards and the alarm (click selects it, no JS), "What to do" replaces "Start recovery", user KPI row, equal-height rows with scrolling lists, hop graph with labels only on victim, exchanges and held funds plus a detail card on hover or keyboard focus. Next: the web page for wallet verification; resolve the Mainnet policy conflict (D-010).
## Evidence
- make check 95 passed, make smoke ok; tests/app/test_web.py updated (What to do, KPIs, full address)
- Screenshots reviewed in the browser against the docker stack (user home, analyst overview, node card)
