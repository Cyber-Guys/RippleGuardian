---
id: T-020
objective: O-1
status: review
owner: nico/claude
branch: t/T-020-mandatory-verification
depends_on: [T-017, T-019]
scope: [src/ixh26/store/repo.py, src/ixh26/app/api.py, src/ixh26/app/views/user_pages.py, src/ixh26/app/templates/user/, src/ixh26/flows/smoke.py, scripts/demo.py, tests/, README.md, docs/, tasks/]
contracts_used: []
policy: "1.1"
---
## Objective
A normal user's wallet is monitored only after the T-017 ownership proof succeeds.
## Acceptance criteria
- [x] Adding a wallet sends the user to the verification page; unverified wallets show "Not watched yet"
- [x] Worker and alerts skip unverified wallets; analysts are exempt
- [x] make check and make smoke green; demo script performs the real proof for its victim
## Out of scope
Migrating existing wallets, a verified flag on the table.
## Log
- 11:38 nico/claude: policy 1.1 acknowledged. Monitoring filter lives in store/repo.py (watched_addresses, watchers) and reads the existing wallet_challenges rows, so no schema change. Repo moved to /home/nico/hackathon/ripple-guardian.
## Evidence
- make check 124 passed; tests/flows/test_flows.py and tests/app/test_frontend_pages.py cover the rule
