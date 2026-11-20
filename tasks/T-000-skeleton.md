---
id: T-000
objective: O-1
status: review
owner: tommaso/a1
branch: t/T-000-skeleton
depends_on: []
scope: [pyproject.toml, uv.lock, Makefile, .env.example, .gitignore, .dockerignore, Dockerfile, docker-compose.yml, README.md, THIRD_PARTY.md, AGENTS.md, src/ixh26/__init__.py, src/ixh26/config.py, src/ixh26/contracts.py, src/ixh26/cli.py, scripts/secret_scan.py, scripts/ci.sh, tests/test_config.py, tests/test_contracts.py, tests/test_cli.py, tests/test_secret_scan.py, .python-version, artifacts/.gitkeep, docs/DECISIONS.md]
contracts_used: []
policy: "1.0"
---
## Objective
The repo has a runnable, dockerized Python skeleton with shared contracts and green `make check` / `make smoke`.
## Acceptance criteria
- [x] `make check` passes (ruff, format, offline tests, secret scan)
- [x] `make smoke` passes
- [x] `docker compose config` validates; `docker compose build` succeeds
- [x] D-001..D-004 drafted in docs/DECISIONS.md (approved by tommaso in chat)
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 21:05 tommaso/a1: policy 1.0 acknowledged; claimed, worktree ../wt-T-000.
- 21:20 tommaso/a1: scope extended (tests/test_cli.py, tests/test_secret_scan.py, .python-version, artifacts/.gitkeep).
- 21:45 tommaso/a1: done, status review. Branch t/T-000-skeleton pushed (19 commits). Waiting for human merge OK.
  Handoff/gotchas: contracts use Decimal only, XRP in integer drops; `ixh26 smoke` delegates to
  `ixh26.flows.smoke:run` once T-004 provides it; `make demo` expects scripts/demo.py (T-005);
  config secrets via `config.jwt_secret()` / `config.wallet_seed(name)` (env XRPL_SEED_<NAME>).
## Evidence
- `make check`: 22 passed (tests/test_config.py, test_contracts.py, test_cli.py, test_secret_scan.py), ruff clean, secret scan ok.
- `make smoke`: "skeleton smoke ok (network=testnet)".
- `docker compose config --quiet` ok; `docker compose build` ok; `docker run ixh26-guardian:dev ixh26 smoke` ok.
- Decisions D-001..D-004 in docs/DECISIONS.md (approved by tommaso in chat, 2026-11-20).
