---
id: T-010
objective: O-1
status: review
owner: nico/claude
branch: t/T-005-testnet-demo
depends_on: [T-000]
scope: [Makefile]
contracts_used: []
policy: "1.0"
---
## Objective
Local (non-docker) runs load `.env`: `make wallets`, `make api`, `make worker`, and `make demo` use `uv run --env-file .env`.
## Acceptance criteria
- [x] `make api` / `make worker` / `make wallets` targets; `make demo` creates missing wallets first
- [x] `make check` and `make smoke` unchanged and green
## Out of scope
Docker (compose already loads .env).
## Log
- 00:45 nico/claude: policy 1.0 acknowledged. Small shared-file task, committed on the T-005 branch because the demo needs it; announce to the team on merge.
- 00:55 nico/claude: targets added; process env wins over .env with uv --env-file (checked), so DATABASE_URL/JWT_SECRET can be overridden per run.
## Evidence
- make check / make smoke green; make wallets + make demo used for the Testnet run in T-005
