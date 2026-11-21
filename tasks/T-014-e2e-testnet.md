---
id: T-014
objective: O-1
status: done
owner: nico/claude
branch: t/T-014-e2e-testnet
depends_on: [T-012, T-013]
scope: [artifacts/, docs/E2E.md, scripts/e2e_browser.py, src/ixh26/app/charts.py, src/ixh26/app/templates/base.html]
contracts_used: []
policy: "1.0"
---
## Objective
Proof on real Testnet that both roles work end to end in a browser.
## Acceptance criteria
- [x] scripted browser run as user and analyst against a fresh Testnet theft
- [x] screenshots in artifacts/screenshots, ledger figures cross-checked with the explorer
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
- 02:05 nico/claude: fresh docker stack, live Testnet theft, ledger cross-check 7/7, Playwright walkthrough both roles. Small fixes found by the run: victim value rounding in the flow graph, sidebar pulse wrapping, e2e script read the flagged address after reload. Merged to master with nico's OK.
## Evidence
- docs/E2E.md (tx links, results table), artifacts/screenshots/*.png, artifacts/tx_log.jsonl
