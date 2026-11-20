---
id: T-009
objective: O-1
status: claimed
owner: nico/claude
branch: t/T-009-contracts-ui-deps
depends_on: [T-000]
scope: [src/ixh26/contracts.py, tests/test_contracts.py, pyproject.toml, uv.lock, THIRD_PARTY.md, docs/DECISIONS.md]
contracts_used: [AlertKind, SecurityEvent, AccountActivity]
policy: "1.0"
---
## Objective
Small contract task: shared types and dependencies needed by the in-app notifications and the web UI.
## Acceptance criteria
- [ ] `AlertKind.FLAGGED_COUNTERPARTY` (in-app notification when a watched wallet touches an analyst-flagged account)
- [ ] `SecurityEvent.tx_index` and `AccountActivity.pre_tx_balances` (needed by the takeover detector of T-006)
- [ ] Jinja2 + python-multipart added, each with a THIRD_PARTY row
- [ ] D-005 (one app, two roles, no personal data, in-app notifications) and D-006 (Jinja2 + HTMX) drafted for human approval
## Out of scope
Any behaviour change.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
## Evidence
