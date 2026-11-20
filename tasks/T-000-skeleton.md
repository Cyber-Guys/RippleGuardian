---
id: T-000
objective: O-1
status: claimed
owner: tommaso/a1
branch: t/T-000-skeleton
depends_on: []
scope: [pyproject.toml, uv.lock, Makefile, .env.example, .gitignore, .dockerignore, Dockerfile, docker-compose.yml, README.md, THIRD_PARTY.md, AGENTS.md, src/ixh26/__init__.py, src/ixh26/config.py, src/ixh26/contracts.py, src/ixh26/cli.py, scripts/secret_scan.py, scripts/ci.sh, tests/test_config.py, tests/test_contracts.py, docs/DECISIONS.md]
contracts_used: []
policy: "1.0"
---
## Objective
The repo has a runnable, dockerized Python skeleton with shared contracts and green `make check` / `make smoke`.
## Acceptance criteria
- [ ] `make check` passes (ruff, format, offline tests, secret scan)
- [ ] `make smoke` passes
- [ ] `docker compose config` validates; `docker compose build` succeeds
- [ ] D-001..D-004 drafted in docs/DECISIONS.md (approved by tommaso in chat)
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
## Evidence
